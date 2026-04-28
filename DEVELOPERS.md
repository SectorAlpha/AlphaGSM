# AlphaGSM Developer Guide

This document is the technical reference for contributors, maintainers, and automation working inside the repository.

Release-facing changes should also update [changelog.txt](changelog.txt).

## Top-Level Architecture

AlphaGSM is a Python CLI that normalises game-server lifecycle management across multiple backends. The core design is:

- one shared command surface
- one persistent per-server datastore
- per-game module implementations for lifecycle details
- a runtime layer that can launch either local screen-backed processes or Docker containers
- dedicated test layers for unit, integration, and streamed smoke coverage

At runtime, the user-facing call path is:

1. `./alphagsm ...`
2. [src/core/main.py](src/core/main.py)
3. server-name parsing, wildcard expansion, and command parsing
4. [src/server/server.py](src/server/server.py) `Server(...)`
5. merge of default commands with module-defined commands
6. dispatch into default server behaviour or module-specific functions
7. runtime resolution through [src/server/runtime.py](src/server/runtime.py)
8. process startup through [src/screen](src/screen) or container startup through Docker

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
  `Server` abstraction, datastore integration, default command set, runtime selection, module loading.
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

## Server Template Naming

Store per-server config examples under `docs/server-templates/<module_name>/`.

- Make the template mimic the real game-owned config file as closely as possible: filename, relative path, key spelling, syntax, comments, and section layout.
- Use the real runtime filename when the module or docs identify one stable on-disk config path, such as `server.cfg`, `server.properties`, `mumble-server.ini`, or `dedicated_cfg.txt`.
- Keep `alphagsm-example.cfg` only when the module exposes AlphaGSM-managed values but does not manage one stable game-owned config filename.
- Match the real relative path when it is part of the contract, for example `ROGame/Config/PCServer-ROGame.ini` or `System/UT2004.ini`.
- Include concrete default values from `configure(...)`, `sync_server_config(...)`, smoke tests, or the matching `docs/servers/<module>.md` guide.
- Do not include AlphaGSM-only datastore keys such as `download_name`, `dir`, `backup`, `image`, or other manager metadata unless the game itself reads them.
- Start from `docs/server-templates/_template/` when adding new template directories.
- Run `python scripts/audit_server_templates.py` after template changes to catch filename mismatches against module- and guide-backed config paths.

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
- `doctor`

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

### Module identity and aliases

Canonical module ids are real Python modules under `src/gamemodules/`.

- Define user-facing aliases and namespace defaults in [src/server/module_aliases.json](src/server/module_aliases.json).
- Resolve module names through [src/server/module_catalog.py](src/server/module_catalog.py) before importing a game module.
- Persist the canonical module id in the server datastore even when the user created the server through an alias such as `tf2` or `cs2server`.
- Do not add wrapper alias files such as `tf2.py` or namespace `DEFAULT.py` shims under `src/gamemodules/`; that routing now lives in the shared catalog.
- Alias keys share the same namespace as canonical ids, and alias values must point directly at a real canonical module id.

Generated parity reporting also works at the canonical-module level:

- [scripts/generate_module_parity_report.py](scripts/generate_module_parity_report.py)
- [docs/module_parity_report.md](docs/module_parity_report.md)
- [docs/module_parity_report.json](docs/module_parity_report.json)

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
| `get_runtime_requirements` | `(server)` | runtime metadata for Docker-capable modules |
| `get_container_spec` | `(server)` | Docker launch spec |

### Optional module functions

| Function | Signature | Purpose |
|---|---|---|
| `prestart` | `(server, *args, **kwargs)` | Run before the screen session starts (e.g. symlink Steam libraries) |
| `poststart` | `(server, *args, **kwargs)` | Run after the screen session starts (e.g. send init commands) |
| `postset` | `(server, key, **kwargs)` | React after a `set` data-store change |
| `setting_schema` | module-level `dict[str, SettingSpec]` | Declare schema-backed `set` keys, aliases, examples, and secrecy for discovery |
| `config_sync_keys` | module-level `tuple[str, ...]` | List datastore keys that should auto-sync into native game config files |
| `sync_server_config` | `(server)` | Rewrite the native config file from datastore-backed values |
| `list_setting_values` | `(server, canonical_key)` | Return enumerable values for schema-backed keys such as maps |
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
- schema-backed `set` keys should use `setting_schema` plus `resolve_requested_key(...)` in the shared `Server.set` flow, with `sync_server_config(server)` handling the on-disk native config update for datastore keys in `config_sync_keys`
- every maintained game module must define `import server.runtime as runtime_module` when it uses shared Docker builders, plus explicit module-scope `get_runtime_requirements(...)` and `get_container_spec(...)` wrappers
- choose the runtime family first, then call `server.runtime` builders or `utils.proton` helpers inside those wrappers; do not rely on runtime inference to add the hooks for you
- Windows-binary modules that already use `utils.proton.wrap_command(...)` should normally build Docker metadata through `utils.proton.get_runtime_requirements(...)` and `utils.proton.get_container_spec(...)` so process and container modes stay aligned
- `set` now preflights any claim-affecting datastore change before persistence, including top-level `port` / `*port` keys, hosted-IP keys (`bindaddress`, `publicip`, `externalip`, `hostip`), and nested runtime `ports` edits
- `setup(...)` now resolves port ownership before `install(...)`; it may auto-shift the whole claimed port group only for default-owned claims, and must preserve earlier explicit user intent across later setup runs
- `start(...)` now performs a strict port-manager preflight before `prestart(...)` and runtime launch

Static enforcement lives in `tests/unit_tests/test_runtime_contract_static.py`, which imports every game module and verifies the Docker runtime hooks are present in module scope.
- Backend runtime coverage is tracked separately in `tests/backend_integration_tests/docker_family_matrix.py`. Keep three declared representative cases per runtime family, and keep the active cases green in CI through `tests/backend_integration_tests/test_backend_docker.py`.
- Cheap backend lifecycle coverage for the shared port-manager path lives in `tests/backend_integration_tests/test_backend_port_manager.py`; keep it green in CI because it proves the cross-runtime `create -> setup -> start -> query -> info -> stop` contract without heavyweight game downloads.
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
- `runtime`
- `runtime_family`
- `dir`
- `port`
- `exe_name`
- `url`
- `version`
- `javapath`
- `image`
- `java_major`
- `container_name`
- `mounts`
- `env`
- `ports`
- `port_claim_policy`
- `network_mode`
- `stop_mode`
- `backup`
- Steam app metadata for Steam-backed servers

Port ownership is derived from:

- top-level `port` and `*port` keys
- hosted-IP keys such as `bindaddress`, `publicip`, `externalip`, and `hostip`
- runtime/container `ports` metadata
- local query/info hooks when they imply an additional claimed local port

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

## Runtime Lifecycle

AlphaGSM resolves a runtime per server:

- `process` by default for the traditional local flow
- `docker` only when `[runtime] backend = docker` is configured and the module exposes explicit runtime hooks

Within `process`, the concrete launcher is selected independently by `[process] backend`:

- `screen`
- `tmux`
- `subprocess`

Core helpers:

- [src/server/runtime.py](src/server/runtime.py)
- [src/screen](src/screen)
- [src/screen/tail.py](src/screen/tail.py)
- [src/utils/proton.py](src/utils/proton.py)

Container image scaffolding currently lives under:

- [docker/README.md](docker/README.md)
- [docker/java/Dockerfile](docker/java/Dockerfile)
- [docker/quake-linux/Dockerfile](docker/quake-linux/Dockerfile)
- [docker/simple-tcp/Dockerfile](docker/simple-tcp/Dockerfile)
- [docker/steamcmd-linux/Dockerfile](docker/steamcmd-linux/Dockerfile)
- [docker/service-console/Dockerfile](docker/service-console/Dockerfile)
- [docker/wine-proton/Dockerfile](docker/wine-proton/Dockerfile)
- [docker/wine-proton/entrypoint.sh](docker/wine-proton/entrypoint.sh)
Lifecycle model:
 [tests/integration_tests](tests/integration_tests)
 ALPHAGSM_RUN_INTEGRATION=1 pytest tests/integration_tests
1. build command line
2. resolve runtime metadata from the datastore and module hooks
3. for `process`, write `screenrc` if needed and start a detached session
4. for `docker`, assemble `docker run` args from the container spec
5. inject console commands through the selected runtime
6. use `doctor` to print the effective runtime decision and local runtime-health checks for a server

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
