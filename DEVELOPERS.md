# AlphaGSM Developer Guide

This document is the technical reference for contributors, maintainers, and automation working inside the repository.

## Top-Level Architecture

AlphaGSM is a Python CLI that normalises game-server lifecycle management across multiple backends. The core design is:

- one shared command surface
- one persistent per-server datastore
- per-game module implementations for lifecycle details
- GNU screen as the long-running process container
- dedicated test layers for unit, integration, and streamed smoke coverage

At runtime, the user-facing call path is:

1. `./alphagsm ...`
2. [src/core/main.py](src/core/main.py)
3. server-name parsing, wildcard expansion, and command parsing
4. [src/server/server.py](src/server/server.py) `Server(...)`
5. merge of default commands with module-defined commands
6. dispatch into default server behaviour or module-specific functions
7. process startup through [src/screen/screen.py](src/screen/screen.py)

## Repository Layout

- [alphagsm](alphagsm)
  User-facing CLI entry point.
- [alphagsm-internal](alphagsm-internal)
  Internal helper used for multi-server and delegated execution paths.
- [alphagsm-downloads](alphagsm-downloads)
  Download-user helper for shared artifact retrieval.
- [core](core)
  CLI dispatch, command routing, subprocess orchestration, multiplexer logic.
- [server](server)
  `Server` abstraction, datastore integration, default command set, module loading.
- [gamemodules](gamemodules)
  Game-specific implementations.
- [downloader](downloader)
  Shared artifact cache and download ownership flow.
- [downloadermodules](downloadermodules)
  Backend-specific download implementations.
- [screen](screen)
  GNU screen orchestration and log helpers.
- [utils](utils)
  Settings, backup scheduling, SteamCMD helpers, command parsing, filesystem update helpers.
- [tests](tests)
  Unit tests.
- [integration_tests](integration_tests)
  Pytest-driven end-to-end tests.
- [smoke_tests](smoke_tests)
  Shell-driven streamed lifecycle runners used by CI and documentation.
- [docs](docs)
  User-facing documentation.

## Command And Server Model

The shared command contract is defined in [src/server/server.py](src/server/server.py).

Default commands:

- `setup`
- `start`
- `stop`
- `activate`
- `deactivate`
- `status`
- `message`
- `connect`
- `dump`
- `set`
- `backup`

Game modules extend this model by exporting module-level data:

- `commands`
- `command_args`
- `command_descriptions`
- `command_functions`

The server object merges these module-level definitions with the defaults at runtime.

## Game Module Contract

A game module is a Python file under `src/gamemodules/`.  The `Server` class
dispatches user commands by calling named attributes on the module.  The full
specification lives in [src/server/gamemodules.py](src/server/gamemodules.py).
The skill-level checklist lives in
[skills/server-lifecycle/SKILL.md](skills/server-lifecycle/SKILL.md).

### Required module attributes

| Attribute | Notes |
|---|---|
| `commands` | Tuple of extra command names beyond the default set (e.g. `("update", "restart")`).  Use `()` if none. |
| `command_args` | Dict mapping command name → `CmdSpec` for all extra commands and any built-in commands whose arg spec the module extends. |
| `command_descriptions` | Dict mapping command name → description string for all extra commands. |
| `command_functions` | Dict mapping command name → callable for all extra commands. |

### Required module functions

| Function | Signature | Backs user command |
|---|---|---|
| `configure` | `(server, ask, *args, **kwargs)` | `setup` |
| `install` | `(server, *args, **kwargs)` | `setup` |
| `get_start_command` | `(server, *args, **kwargs)` | `start` |
| `do_stop` | `(server, time, *args, **kwargs)` | `stop` |
| `status` | `(server, verbose, *args, **kwargs)` | `status` |
| `message` | `(server, message, *args, **kwargs)` | `message` |
| `backup` | `(server, *args, **kwargs)` | `backup` |
| `checkvalue` | `(server, key, *values, **kwargs)` | `set` |

### Optional module functions

| Function | Signature | Purpose |
|---|---|---|
| `prestart` | `(server, *args, **kwargs)` | Run before the screen session starts (e.g. symlink Steam libraries) |
| `poststart` | `(server, *args, **kwargs)` | Run after the screen session starts (e.g. send init commands) |
| `postset` | `(server, key, **kwargs)` | React after a `set` data-store change |
| `get_query_address` | `(server)` | Return `(host, port, protocol)` for `query`; protocols: `"a2s"`, `"quake"`, `"ts3"`, `"tcp"` |
| `get_info_address` | `(server)` | Return `(host, port, protocol)` for `info`; protocols: `"a2s"`, `"slp"`, `"tcp"`.  Always add this unless the module uses `define_valve_server_module()`. |
| `update` | `(server, validate=False, restart=False, ...)` | In-place server update; wire into `commands` / `command_functions` |
| `restart` | `(server, ...)` | Custom restart logic if the default stop+start is insufficient |
| `wipe` | `(server)` | Delete world/save data; alternatively set `wipe_paths` attribute |
| `max_stop_wait` | attribute `int` | Max minutes to wait for graceful stop (default 5, capped at 5) |

### Operational expectations

- `configure(...)` stores at minimum `port` and `dir` in `server.data`, initialises the backup data structure, and returns `(args, kwargs)` to forward to `install`
- `install(...)` ensures the server filesystem is in a runnable state and calls `server.data.save()`
- `get_start_command(...)` returns `(argv_list, working_dir)`
- `checkvalue(...)` delegates `"backup"` key paths to `backup_utils.checkdatavalue`
- `get_info_address(...)` prevents `Server.info()` from falling back to the TCP ping last resort

### Representative implementations

- [src/gamemodules/minecraft/vanilla.py](src/gamemodules/minecraft/vanilla.py)
- [src/gamemodules/teamfortress2.py](src/gamemodules/teamfortress2.py)
- [src/gamemodules/projectzomboid.py](src/gamemodules/projectzomboid.py)
- [src/gamemodules/counterstrikeglobaloffensive.py](src/gamemodules/counterstrikeglobaloffensive.py)
- [src/gamemodules/readyornotserver.py](src/gamemodules/readyornotserver.py) — example with `get_query_address` and `get_info_address`

## Datastore Model

Per-server state is persisted as JSON under the configured server datapath.

Primary files:

- [src/server/data.py](src/server/data.py)
- [src/server/server.py](src/server/server.py)

Typical persisted keys include:

- `module`
- `dir`
- `port`
- `exe_name`
- `url`
- `version`
- `javapath`
- `backup`
- Steam app metadata for Steam-backed servers

## Download And Install Pipeline

The download subsystem is split between:

- [src/downloader/downloader.py](src/downloader/downloader.py)
  cache lookup, lock handling, and shared-download ownership
- [src/downloadermodules/url.py](src/downloadermodules/url.py)
  HTTP download and decompression
- [src/utils/steamcmd.py](src/utils/steamcmd.py)
  SteamCMD bootstrap and Steam app installation

Known exception:

- [src/downloadermodules/steamcmd.py](src/downloadermodules/steamcmd.py) is currently legacy parser-broken code and remains outside the maintained lint/doc verification surface

## Screen Lifecycle

AlphaGSM uses GNU screen as the process supervisor for long-running game servers.

Core helpers:

- [src/screen/screen.py](src/screen/screen.py)
- [src/screen/tail.py](src/screen/tail.py)
Lifecycle model:
 [tests/integration_tests](tests/integration_tests)
 ALPHAGSM_RUN_INTEGRATION=1 pytest tests/integration_tests
1. build command line
2. write `screenrc` if needed
3. start detached session
4. inject console commands with `screen ... stuff`

 [tests/smoke_tests](tests/smoke_tests)
 bash ./tests/smoke_tests/run_minecraft_vanilla.sh
 bash ./tests/smoke_tests/run_tf2.sh
The smoke runners are the best repository examples of the real lifecycle a user should follow:

- [smoke_tests/run_minecraft_vanilla.sh](smoke_tests/run_minecraft_vanilla.sh)
- [smoke_tests/run_tf2.sh](smoke_tests/run_tf2.sh)

`gmodserver` install behaviour:
- download common mountable Source content into `<install_dir>/_gmod_content/` instead of the server root
- write `garrysmod/cfg/mount.cfg` entries for `cstrike`, `hl2mp`, and `tf`
- seed `garrysmod/cfg/mountdepots.txt` with Facepunch's default depot list

 [tests/smoke_tests/run_minecraft_vanilla.sh](tests/smoke_tests/run_minecraft_vanilla.sh)
 [tests/smoke_tests/run_tf2.sh](tests/smoke_tests/run_tf2.sh)
- create isolated temporary configs
- show the exact command sequence a real operator would use
- stream command output directly into CI logs
- verify readiness and shutdown using server-aware checks

For documentation changes, prefer the smoke tests over hand-written examples.

pytest tests
```

  --cov=core \
  --cov=downloader \
  --cov=downloadermodules \
  --cov=gamemodules \
  --cov=screen \
  --cov=server \
  --cov=utils \
  --cov-report=xml


Location:

- [integration_tests](integration_tests)
Command:

```bash
ALPHAGSM_RUN_INTEGRATION=1 pytest integration_tests
```

### Smoke tests

Command:

```bash
bash ./smoke_tests/run_minecraft_vanilla.sh
bash ./smoke_tests/run_tf2.sh
```

## Linting

Lint is driven by [lint.sh](lint.sh).

Properties of the current lint pipeline:

- enumerates maintained Python files under the primary source trees
- excludes the parser-broken legacy `src/downloadermodules/steamcmd.py`
- runs pylint through the selected interpreter
- enforces `--fail-under=10`

Command:

```bash
bash ./lint.sh
```

## CI Topology

The GitHub Actions workflow is [`.github/workflows/unittest.yaml`](.github/workflows/unittest.yaml).

Current job layout:

1. `build`
2. `lint`
3. `unit-test`
4. matrix `smoke-test`
5. matrix `integration-test`

Triggers:

- push to `master`
- pull request targeting `master`

Current matrix targets:

- Minecraft vanilla
- TF2

There is also a documentation publishing workflow:

- [`.github/workflows/wiki-sync.yaml`](.github/workflows/wiki-sync.yaml)

That workflow mirrors selected repository docs into the GitHub wiki by pushing to the wiki repository.

## Configuration

Main template:

- [alphagsm.conf-template](alphagsm.conf-template)

Important environment variables:

- `ALPHAGSM_CONFIG_LOCATION`
- `ALPHAGSM_USERCONFIG_LOCATION`
- `ALPHAGSM_RUN_INTEGRATION`
- `ALPHAGSM_DEBUG`

The smoke tests rely on temporary config files and `ALPHAGSM_CONFIG_LOCATION` to isolate state per run.

## Documentation Contract

Documentation is now deliberately split by audience:

1. [README.md](README.md)
   non-technical, copy-paste-first usage
2. [docs](docs)
   user-facing server guides
3. [DEVELOPERS.md](DEVELOPERS.md)
   technical architecture and maintenance notes

When behaviour changes:

- update smoke tests if the real workflow changed
- update server guides if user steps changed
- update `README.md` if first-run commands changed
- update `DEVELOPERS.md` if architecture, CI, or maintenance expectations changed

The repository is the source of truth. The wiki is a published mirror generated from tracked docs by `scripts/publish_wiki.sh`.

## Repo Automation Files

Repo-local automation guidance now lives in:

- [AGENTS.md](AGENTS.md)
- [skills/smoke-driven-docs/SKILL.md](skills/smoke-driven-docs/SKILL.md)
- [skills/server-lifecycle/SKILL.md](skills/server-lifecycle/SKILL.md)
