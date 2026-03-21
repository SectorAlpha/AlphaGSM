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
2. [core/main.py](core/main.py)
3. server-name parsing, wildcard expansion, and command parsing
4. [server/server.py](server/server.py) `Server(...)`
5. merge of default commands with module-defined commands
6. dispatch into default server behaviour or module-specific functions
7. process startup through [screen/screen.py](screen/screen.py)

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

The shared command contract is defined in [server/server.py](server/server.py).

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

A game module typically implements some or all of:

- `configure(server, ask, ...)`
- `install(server, ...)`
- `get_start_command(server)`
- `do_stop(server, ...)`
- `status(server, verbose)`
- `message(...)`
- `update(...)`
- `restart(...)`
- `prestart(...)`
- `backup(...)`

Operational expectations:

- `configure(...)` stores resolved user choices in `server.data`
- `install(...)` ensures the server filesystem is in a runnable state
- `get_start_command(...)` returns the command tuple the default `start` path consumes
- `prestart(...)` is optional and performs just-in-time environment setup

Representative implementations:

- [gamemodules/minecraft/vanilla.py](gamemodules/minecraft/vanilla.py)
- [gamemodules/teamfortress2.py](gamemodules/teamfortress2.py)
- [gamemodules/counterstrikeglobaloffensive.py](gamemodules/counterstrikeglobaloffensive.py)

## Datastore Model

Per-server state is persisted as JSON under the configured server datapath.

Primary files:

- [server/data.py](server/data.py)
- [server/server.py](server/server.py)

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

- [downloader/downloader.py](downloader/downloader.py)
  cache lookup, lock handling, and shared-download ownership
- [downloadermodules/url.py](downloadermodules/url.py)
  HTTP download and decompression
- [utils/steamcmd.py](utils/steamcmd.py)
  SteamCMD bootstrap and Steam app installation

Known exception:

- [downloadermodules/steamcmd.py](downloadermodules/steamcmd.py) is currently legacy parser-broken code and remains outside the maintained lint/doc verification surface

## Screen Lifecycle

AlphaGSM uses GNU screen as the process supervisor for long-running game servers.

Core helpers:

- [screen/screen.py](screen/screen.py)
- [screen/tail.py](screen/tail.py)

Lifecycle model:

1. build command line
2. write `screenrc` if needed
3. start detached session
4. inject console commands with `screen ... stuff`
5. inspect screen logs for troubleshooting or readiness

## Smoke Tests As Executable Documentation

The smoke runners are the best repository examples of the real lifecycle a user should follow:

- [smoke_tests/run_minecraft_vanilla.sh](smoke_tests/run_minecraft_vanilla.sh)
- [smoke_tests/run_tf2.sh](smoke_tests/run_tf2.sh)

They are important because they:

- create isolated temporary configs
- show the exact command sequence a real operator would use
- stream command output directly into CI logs
- verify readiness and shutdown using server-aware checks

For documentation changes, prefer the smoke tests over hand-written examples.

## Test Layers

### Unit tests

Location:

- [tests](tests)

Command:

```bash
pytest tests
```

Coverage command:

```bash
pytest tests \
  --cov=core \
  --cov=downloader \
  --cov=downloadermodules \
  --cov=gamemodules \
  --cov=screen \
  --cov=server \
  --cov=utils \
  --cov-report=term-missing \
  --cov-report=xml
```

### Integration tests

Location:

- [integration_tests](integration_tests)

Command:

```bash
ALPHAGSM_RUN_INTEGRATION=1 pytest integration_tests
```

### Smoke tests

Location:

- [smoke_tests](smoke_tests)

Command:

```bash
bash ./smoke_tests/run_minecraft_vanilla.sh
bash ./smoke_tests/run_tf2.sh
```

## Linting

Lint is driven by [lint.sh](lint.sh).

Properties of the current lint pipeline:

- enumerates maintained Python files under the primary source trees
- excludes the parser-broken legacy `downloadermodules/steamcmd.py`
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

## Repo Automation Files

Repo-local automation guidance now lives in:

- [AGENTS.md](AGENTS.md)
- [skills/smoke-driven-docs/SKILL.md](skills/smoke-driven-docs/SKILL.md)
- [skills/server-lifecycle/SKILL.md](skills/server-lifecycle/SKILL.md)
