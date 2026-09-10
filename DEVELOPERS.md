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

## Documentation Split

Keep repository docs split by audience and preferred operator path:

- [README.md](README.md) should stay simple and lead users toward the Docker
  manager quick-start first, then the host Docker-runtime path, with direct
  host-process usage documented as the fallback.
- [docs/](docs/) should hold the primary user-facing workflows and server
  guides. After the Docker-first migration, [docs/docker-manager.md](docs/docker-manager.md)
  and [docs/docker-runtime-host.md](docs/docker-runtime-host.md) are the main
  runtime-entry docs.
- [DEVELOPERS.md](DEVELOPERS.md) is for implementation details, contracts,
  architecture, and contributor-facing guidance.

## Adding A New Game Server

The operator-facing walkthrough lives in
[docs/adding-a-game-server.md](docs/adding-a-game-server.md). Use that page as
the contribution entry point. This section is the technical checklist.

A new top-level game is a package under `src/gamemodules/<module_id>/` with
`__init__.py` as the public import surface and `main.py` as the implementation.
Users then run the same commands they already know: `create`, `setup`, `start`,
`status`, `query`, `info`, `stop`.

Copy the closest working module:

- Palworld — custom SteamCMD download plus game-specific settings layout
- HL2DM — `define_valve_server_module()` plus shared runtime port constants
- Minecraft Vanilla — Java runtime family

Set `module_contract_version = 1` on the public surface so AlphaGSM can reject
malformed hook exports before runtime inference. Version 1 does not prove that
the dedicated server starts.

A module is incomplete until it lands with:

- required lifecycle and Docker hooks on the public import surface
- unit tests under `tests/unit_tests/`
- an integration test under `tests/integration_tests/test_<module>.py` that
  drives AlphaGSM commands through create, setup, start, readiness, status,
  query, info, info --json, and stop
- a smoke runner under `tests/smoke_tests/run_<module>.sh`
- `docs/servers/<module_id>.md`, a changelog entry, and a tracker update once
  the lifecycle is actually proven

Do not treat hibernation, TCP fallback, or a skipped timeout as a pass.

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
- [core](src/core)
  CLI dispatch, command routing, subprocess orchestration, multiplexer logic.
- [server](src/server)
  `Server` abstraction, datastore integration, default command set, runtime selection, module loading.
- [gamemodules](src/gamemodules)
  Game-specific implementations.
- [downloader](src/downloader)
  Shared artifact cache and download ownership flow.
- [downloadermodules](src/downloadermodules)
  Backend-specific download implementations.
- [screen](src/screen)
  GNU screen orchestration and log helpers.
- [utils](src/utils)
  Settings, backup scheduling, SteamCMD helpers, command parsing, filesystem update helpers.
- [tests/unit_tests](tests/unit_tests)
  Unit tests.
- [tests/integration_tests](tests/integration_tests)
  Pytest-driven end-to-end tests.
- [tests/smoke_tests](tests/smoke_tests)
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

A canonical top-level game module is a package directory under
`src/gamemodules/<name>/` with an `__init__.py` import surface. The `Server`
class dispatches user commands by calling named attributes on the canonical
module import surface. The full specification lives in
[src/server/gamemodules.py](src/server/gamemodules.py). The skill-level
checklist lives in [skills/server-lifecycle/SKILL.md](skills/server-lifecycle/SKILL.md).

Modules may opt into structural validation by setting
`module_contract_version = 1` on the public import surface. Unversioned modules
keep the existing loading path. Version 1 is checked before legacy runtime-hook
inference and proves that required hooks are directly exported callables and
that declared config-sync keys are well formed. It does not prove native config
completeness, provider credentials, signatures, or that the server can start.

Ownership of game-module behaviour stays split:

| Owner | Responsibility |
| --- | --- |
| Manager | Command sequencing, persistence, port ownership, provider/platform enforcement, runtime selection, and lifecycle error handling. |
| Shared operation | A bounded action such as downloading files, rewriting a particular config format, or constructing a runtime spec. |
| Family builder | Defaults and behavior proven equivalent across an engine family. |
| Game module | Select operations, order them, validate game-specific values, and implement engine/install/runtime exceptions. |

Extract a shared helper only when both the successful semantics and the error
behaviour are shared. Keep small duplication when stop/restart sequencing,
config rewrites, or game-specific layout work differ. An exception can replace
a whole hook or call shared operations in a custom order; it must not require a
new global flag, and shared helpers must not branch on canonical game IDs.

Palworld is the custom-install example: it calls the reusable SteamCMD download
operation, then prepares `PalWorldSettings.ini` itself. It does not wrap the
generic install factory, because that factory also owns optional config sync
and post-download callbacks that Palworld does not use.

```python
def install(server):
    os.makedirs(server.data["dir"], exist_ok=True)
    installers.download_steamcmd(
        server,
        steamcmd_module=steamcmd,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    _finalize_install_layout(server)
```

Half-Life 2: Deathmatch is the family-composition example: it keeps
`define_valve_server_module()`, combines addon commands, and declares shared
runtime constants once for both Docker wrappers.

```python
module_contract_version = 1
RUNTIME_FAMILY = "steamcmd-linux"
PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "clientport", "protocol": "udp"},
    {"key": "sourcetvport", "protocol": "udp"},
)
```

Keep `define_valve_server_module()` for Valve-family defaults. Do not replace it
with a universal builder, base-class hierarchy, mixin system, or hook event bus.

For top-level game modules, keep the implementation in `main.py` and reserve
`__init__.py` for the canonical re-export surface.

### Module identity and aliases

Canonical module ids are real top-level package names under `src/gamemodules/`.

- Define user-facing aliases and namespace defaults in [src/server/module_aliases.json](src/server/module_aliases.json).
- Resolve module names through [src/server/module_catalog.py](src/server/module_catalog.py) before importing a game module.
- Persist the canonical module id in the server datastore even when the user created the server through an alias such as `tf2` or `cs2server`.
- Do not add wrapper alias files such as `tf2.py` or namespace `DEFAULT.py` shims under `src/gamemodules/`; that routing now lives in the shared catalog.
- Alias keys share the same namespace as canonical ids, and alias values must point directly at a real canonical module id.
- For package-backed canonical modules, the directory name is the canonical id and `__init__.py` is the only public import surface that `Server(...)`, parity tooling, and static contract tests should treat as canonical.
- Keep package internals such as `main.py`, `mods.py`, `layout.py`, or `workshop.py` as private implementation files. They do not get separate alias entries, parity rows, or standalone module identities.
- When converting a file-backed module into a package-backed canonical module, preserve the exported lifecycle hooks from `__init__.py` so `import gamemodules.<module_id>` keeps working for existing callers and tests.

Generated parity reporting also works at the canonical-module level:

- [scripts/generate_module_parity_report.py](scripts/generate_module_parity_report.py)
- [docs/module_parity_report.md](docs/module_parity_report.md)
- [docs/module_parity_report.json](docs/module_parity_report.json)
- [src/server/module_capabilities.json](src/server/module_capabilities.json)

After changing module capabilities such as `config_sync_keys`, run
`python3 scripts/generate_module_parity_report.py` and commit all generated
changes. Verify with `python3 scripts/generate_module_parity_report.py --check`;
CI runs this separately before the unit suite.

Generated server-support tracking is derived from the checked-in integration
status report:

- [scripts/generate_game_server_support_tracker.py](scripts/generate_game_server_support_tracker.py)
- [docs/TEST_STATUS.md](docs/TEST_STATUS.md)
- [docs/game-server-support.md](docs/game-server-support.md)

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
| `setting_schema` | module-level `dict[str, SettingSpec]` | Declare schema-backed `set` keys, aliases, examples, and secrecy for discovery; entries with `secret=True` are automatically routed to the mode-0o600 secrets file (see [Secrets File](#secrets-file)) |
| `config_sync_keys` | module-level `tuple[str, ...]` | List datastore keys that should auto-sync into native game config files |
| `sync_server_config` | `(server)` | Rewrite the native config file from datastore-backed values |
| `list_setting_values` | `(server, canonical_key)` | Return enumerable values for schema-backed keys such as maps |
| `get_query_address` | `(server)` | Return `(host, port, protocol)` for `query`; protocols include `"a2s"`, `"quake"`, `"source_rcon"`, `"ts3"`, and `"tcp"` |
| `get_info_address` | `(server)` | Return `(host, port, protocol)` for `info`; protocols include `"a2s"`, `"slp"`, `"source_rcon"`, and `"tcp"`. Always add this unless the module uses `define_valve_server_module()`. |
| `update` | `(server, validate=False, restart=False, ...)` | In-place server update; wire into `commands` / `command_functions` |
| `restart` | `(server, ...)` | Custom restart logic if the default stop+start is insufficient |
| `get_wipe_paths` | `(server)` | Return explicit relative world-data paths for the shared preview/confirmation/deletion flow; fixed `wipe_paths` lists also work |
| `get_wipe_root` | `(server)` | Optional explicit world-data root (default: install directory), e.g. Necesse's configured `datadir` |
| `max_stop_wait` | attribute `int` | Max minutes to wait for graceful stop (default 5, capped at 5) |

### World lifecycle options

Keep native interactive world selection available. Terraria/TShock and Necesse
expose a one-launch `start --autocreate` option for fresh unattended fixtures;
tests must opt in explicitly. If the configured world path already exists,
including an unreadable file or symlink, the option produces exactly the plain
start command. Existence checks use host paths even when building Docker specs.
Necesse explicitly mounts its data directory and passes the container path to Java.
Minecraft and Rust already generate missing worlds in their normal launch flow.

`reset-world` and `wipe` share `server.worlds.wipe_worlds`. Module hooks only
resolve targets; core code validates relative paths, rejects symlinked targets
and parents, prints the plan, confirms by default (`-Y` / `--yes` bypass),
rechecks the stopped state and plan, then deletes those targets. Directory
entries mean recursive removal of their contents. Unpreviewable module `wipe`
callbacks are no longer executed. Do not return an entire install/config/plugin
root or guess a native save location. See [world management](docs/world-management.md).

### Shared mod-support foundation

Curated server-side mod support now has a shared core under
[src/server/modsupport](src/server/modsupport).

- `registry.py` resolves module-local curated registries from family plus optional channel/version into a concrete release id, URL, allowed hosts, archive type, and approved destination roots.
- `downloads.py` owns trusted-host validation, optional checksum enforcement, safe archive extraction, and destination allowlisting so AlphaGSM only installs files into explicitly approved server paths.
- `ownership.py` records the AlphaGSM-owned relative file manifest for each installed curated entry.
- `providers.py` owns shared external-provider helpers such as GameBanana item resolution, Mod DB page resolution, Workshop id validation, and direct URL normalization for plugin-style modules. These providers are not TF2-specific; individual game modules decide whether and how to install their payloads safely.
- `plugin_jars.py` packages the repeated desired-state, checked-in manifest resolution, dependency expansion, direct URL handling for plugin payloads, Mod DB archive installs, and owned-file cleanup flow for plugin-style modules such as Paper, the proxy family, and TShock.
- `source_addons.py` packages the repeated desired-state, manifest registry loading, archive staging, GameBanana/Mod DB/workshop intake, direct single-file URL handling, and owned-file cleanup flow for Source-engine games that install addons under a known game directory.
- Thin Source wrappers that share the same `addons/` layout can reuse one checked-in registry under [src/gamemodules/source_curated_mods.json](src/gamemodules/source_curated_mods.json) via `load_shared_source_curated_registry()` instead of carrying identical MetaMod/SourceMod manifests per module.
- `reconcile.py` compares desired vs installed state so modules can add missing curated entries and remove only files that AlphaGSM previously recorded as owned.

Modules that opt into curated mod support still own the game-specific layer:

- keep the canonical module import surface stable, even when the implementation is package-backed
- seed and persist the module-specific `mods` datastore shape
- expose module commands such as `mod add ...`, `mod list`, and `mod apply`
- ship the curated registry file beside the module package and keep its destination rules aligned with the real game layout
- validate provider-specific desired entries such as curated families or workshop ids before saving them
- fail clearly and non-destructively when a provider is still experimental or not yet verified for apply-time installation

When a module supports more than one source class, keep the distinction explicit:

- `manifest` or `curated` means AlphaGSM owns the catalog entry through a checked-in registry file and resolves a known family plus optional channel/version into a concrete release.
- provider-backed sources such as `gamebanana`, `workshop`, or `moddb` mean the user supplied either an external item id or a canonical provider page URL and AlphaGSM resolves live metadata from that provider at apply time.
- direct `url` sources mean the user supplied a concrete download URL and AlphaGSM still validates scheme, filename shape, destination roots, and owned-file cleanup through the shared mod-support layer.
- Treat provider-id sources as shared integrations that can be reused across modules; do not bury provider-resolution code under one game package unless the upstream service is genuinely game-specific.
- Prefer documenting `manifest` as the public user-facing term when the command surface needs to distinguish AlphaGSM-owned entries from external provider ids, but keep `curated` accepted when older commands or datastore state already use that name.
- Keep these source classes separate in the datastore so support expectations, reproducibility, and future update semantics stay clear.

### Operational expectations

- `configure(...)` stores at minimum `port` and `dir` in `server.data`, initialises the backup data structure, and returns `(args, kwargs)` to forward to `install`
- `install(...)` ensures the server filesystem is in a runnable state and calls `server.data.save()`
- `get_start_command(...)` returns `(argv_list, working_dir)`

Validating `get_start_command` implementations
---------------------------------------------

Use the provided script to statically validate gamemodules' `get_start_command` shape:

```bash
python3 scripts/validate_start_commands.py
```

This script performs a conservative check that `get_start_command` returns a tuple
containing an argv-style list and a working-directory path (commonly `server.data["dir"]`).
If you need a simple inventory of modules missing `get_start_command`, run:

```bash
python3 scripts/list_missing_start_commands.py
```

- schema-backed `set` keys should use `setting_schema` plus `resolve_requested_key(...)` in the shared `Server.set` flow, with `sync_server_config(server)` handling the on-disk native config update for datastore keys in `config_sync_keys`
- every maintained game module must define `import server.runtime as runtime_module` when it uses shared Docker builders, plus explicit module-scope `get_runtime_requirements(...)` and `get_container_spec(...)` wrappers
- choose the runtime family first, then call `server.runtime` builders or `utils.proton` helpers inside those wrappers; do not rely on runtime inference to add the hooks for you
- Windows-binary modules that already use `utils.proton.wrap_command(...)` should normally build Docker metadata through `utils.proton.get_runtime_requirements(...)` and `utils.proton.get_container_spec(...)` so process and container modes stay aligned
- when a process-runtime launch depends on a host-installed command, Java runtime, or shared library, prefer declaring it in `host_dependencies` through the module's `get_runtime_requirements(...)` output instead of raising an ad hoc `prestart(...)` error; the shared runtime gate now blocks `screen`, `tmux`, and subprocess launches before start, renders platform-aware install guidance for Linux/macOS/Windows when provided, and recommends the Docker runtime as the fallback path
- scope host dependencies with `platforms` when they only apply on one OS. For example, Linux-only headless wrappers that invoke `xvfb-run` should declare an `xvfb-run` dependency with `platforms=("linux",)` so Windows/macOS local launches do not get a false Wine/Xvfb requirement
- keep Linux headless wrapper metadata aligned with the real launcher surface. If a module or launch script invokes `xvfb-run`, declare it in `host_dependencies`; `tests/unit_tests/test_runtime_contract_static.py` now audits that contract repo-wide
- Linux-native containers that cannot run as root may opt into `run_as_host_user` through both runtime wrappers. Keep the game command unchanged: the shared Docker runtime adds `--user <effective UID>:<effective GID>`, sets the declared absolute `container_home`, and mounts a per-server HOME from `<manager-root>/runtime/<server>/home`.
- `run_as_host_user` is deliberately opt-in and rejects an effective UID of `0`. Do not add module-specific `useradd`, `chown`, `chmod`, HOME-directory creation, or process-versus-Docker command branches; declare the requirement and let `server.runtime` enforce it.
- The `alphagsm-docker` wrapper derives the manager UID from Bash's read-only effective-process identity and the primary GID through a trusted absolute system `id` executable, then reads the Docker supplementary GID from the socket. It does not trust caller `PATH` or identity variables. It reuses a running manager only when Docker reports that exact identity/group tuple and exactly one matching Docker socket mount source. Before recreating an old root, stale-group, or stale-socket manager through the active mode, it walks existing state without following symlinks and fails before mutation if that state is not writable/traversable by the new non-root identity.
- Host-user HOME state must remain outside the writable game-content mount. The runtime normalizes mount targets, rejects duplicate or read-only HOME mounts, validates existing manager-state components without following symlinks, and creates missing components with directory-relative no-follow operations. `doctor` uses the same non-mutating validation and reports whether first-run state is safely creatable.
- `set` now preflights any claim-affecting datastore change before persistence, including top-level `port` / `*port` keys, hosted-IP keys (`bindaddress`, `publicip`, `externalip`, `hostip`), and nested runtime `ports` edits
- `setup(...)` now resolves port ownership before `install(...)`; it may auto-shift the whole claimed port group only for default-owned claims, and must preserve earlier explicit user intent across later setup runs
- `start(...)` now performs a strict port-manager preflight before `prestart(...)` and runtime launch

Static enforcement lives in `tests/unit_tests/test_runtime_contract_static.py`, which imports every game module and verifies the Docker runtime hooks are present in module scope.
- Backend runtime coverage is tracked separately in `tests/backend_integration_tests/docker_family_matrix.py`. Keep three declared representative cases per runtime family, and keep the active cases green in CI through `tests/backend_integration_tests/test_backend_docker.py`.
- Cheap backend lifecycle coverage for the shared port-manager path lives in `tests/backend_integration_tests/test_backend_port_manager.py`; keep it green in CI because it proves the cross-runtime `create -> setup -> start -> query -> info -> stop` contract without heavyweight game downloads.
- Integration tests should now prefer module-aware Docker selection instead of hard-coding `runtime_backend="docker"` per file. In `tests/integration_tests/conftest.py`, call `write_config(..., runtime_backend="auto", module_name="<canonical module id>")` for container-capable modules so the harness uses the module's explicit Docker contract and branch-local runtime images by default, while still falling back to plain process mode for modules that do not declare container support.
- Keep the integration config dual-wired: `write_config(...)` now writes both `[process]` and `[docker]` sections on purpose. That lets Docker-first integration configs fall back cleanly if a test probes a non-container module, and it avoids breaking process-only servers when shared runtime-image work is in flight.
- `checkvalue(...)` delegates `"backup"` key paths to `backup_utils.checkdatavalue`
- `get_info_address(...)` prevents `Server.info()` from falling back to the TCP ping last resort

### Representative implementations

- [src/gamemodules/palworld/](src/gamemodules/palworld/) — custom SteamCMD install composition
- [src/gamemodules/hl2dmserver/](src/gamemodules/hl2dmserver/) — Valve family plus explicit Docker ports
- [src/gamemodules/minecraft/vanilla.py](src/gamemodules/minecraft/vanilla.py) — Java family
- [src/gamemodules/teamfortress2/](src/gamemodules/teamfortress2/) — Source family with curated addons
- [src/gamemodules/readyornotserver/](src/gamemodules/readyornotserver/) — example with `get_query_address` and `get_info_address`

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

### Secrets File

Keys declared as `secret=True` in a module's `setting_schema` are stored in a separate
`<name>.secrets.json` file rather than the main `<name>.json` data file.

- `Server.__init__` calls `_configure_secret_split()` immediately after the module is loaded.
  That method collects every storage key whose `SettingSpec` carries `secret=True` and passes
  them to `JSONDataStore.set_secret_keys(keys, secrets_path)`.
- At save time the data store writes secret keys exclusively to `<name>.secrets.json` using
  `os.open(…, O_WRONLY | O_CREAT | O_TRUNC, 0o600)` so the file is never readable by other
  system users. It then `os.chmod`s the file to enforce `0o600` after write.
- At load time the data store merges the secrets file back into the in-memory dict, so the
  rest of the code operates on a single unified namespace.
- `alphagsm data` (which calls `prettydump()`) redacts any non-empty secret value as
  `<redacted>` rather than printing the plaintext.
- If a module has no `setting_schema`, or none of its schema entries carry `secret=True`,
  no secrets file is created and the data store behaves exactly as before.

To mark a password or token field as secret in a new or existing module:

```python
from server.settable_keys import SettingSpec

setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
}
```

Modules that only need secrecy and have no other schema requirements can provide a minimal
`setting_schema` containing only the password entries. Non-password `set` operations on
non-schema keys still fall through to `checkvalue` / `str_keys` unchanged.

## Download And Install Pipeline

The download subsystem is split between:

- [src/downloader/downloader.py](src/downloader/downloader.py)
  cache lookup, lock handling, and shared-download ownership
- [src/downloadermodules/url.py](src/downloadermodules/url.py)
  HTTP download and decompression
- [src/utils/steamcmd.py](src/utils/steamcmd.py)
  SteamCMD bootstrap and Steam app installation

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

Modules with derived or protocol-specific port layouts should expose one
module-scope `port_claim_definitions` tuple and reuse it when building
`get_runtime_requirements(server)` and `get_container_spec(server)`. Each
definition uses `key` and `protocol`, with an optional integer `offset` from
the datastore value named by `key`; for example, `{"key": "port", "offset":
1, "protocol": "udp"}` describes `port + 1`. The shared
`server.runtime.build_port_specs(...)` helper validates the derived host and
container ports are within `1..65535`, and the port manager consumes the same
definitions for process and Docker ownership checks. Keep runtime selection
out of this game-module contract: a module declares what the server needs,
while the shared runtime layer decides how those ports are launched and
published.

Container image scaffolding currently lives under:

- [docker/README.md](docker/README.md)
- [docker/java/Dockerfile](docker/java/Dockerfile)
- [docker/quake-linux/Dockerfile](docker/quake-linux/Dockerfile)
- [docker/simple-tcp/Dockerfile](docker/simple-tcp/Dockerfile)
- [docker/steamcmd-linux/Dockerfile](docker/steamcmd-linux/Dockerfile)
- [docker/service-console/Dockerfile](docker/service-console/Dockerfile)
- [docker/wine-proton/Dockerfile](docker/wine-proton/Dockerfile)
- [docker/wine-proton/entrypoint.sh](docker/wine-proton/entrypoint.sh)

The shared Ubuntu 24.04 runtime images intentionally carry a small set of
legacy compatibility packages for older dedicated-server binaries that still
link against removed distro libraries, currently including `libssl1.1`,
`libssl1.0.0`, and `libprotobuf10`. When one of these packages becomes a real
host requirement for process-backed users, document the matching install step
in [README.md](README.md) and the affected server guide under `docs/servers/`.

Lifecycle model:

1. build command line
2. resolve runtime metadata from the datastore and module hooks
3. claim the module's complete port set before runtime-specific launch work
4. for `process`, write `screenrc` if needed and start a detached session
5. for `docker`, assemble `docker run` args from the container spec
6. inject console commands through the selected runtime
7. use `doctor` to print the effective runtime decision and local runtime-health checks for a server

### Integration tests

Integration tests live under [tests/integration_tests](tests/integration_tests).
Run the repository target with:

```bash
make integration-test
```

### Smoke tests

Smoke tests live under [tests/smoke_tests](tests/smoke_tests). Run all smoke
tests with:

```bash
make smoke-test
```

The canonical smoke runners are:

- [tests/smoke_tests/run_minecraft_vanilla.sh](tests/smoke_tests/run_minecraft_vanilla.sh)
- [tests/smoke_tests/run_tf2.sh](tests/smoke_tests/run_tf2.sh)

Run one runner through the Make target with, for example:

```bash
make smoke-test SMOKE_TEST=run_minecraft_vanilla.sh
```

The smoke runners are the best repository examples of the real lifecycle a
user should follow. They:

- create isolated temporary configs
- show the exact command sequence a real operator would use
- stream command output directly into CI logs
- verify readiness and shutdown using server-aware checks

`gmodserver` install behaviour:

- download common mountable Source content into `<install_dir>/_gmod_content/` instead of the server root
- write `garrysmod/cfg/mount.cfg` entries for `cstrike`, `hl2mp`, and `tf`
- seed `garrysmod/cfg/mountdepots.txt` with Facepunch's default depot list

For documentation changes, prefer the smoke tests over hand-written examples.

## Linting

Lint is driven by [lint.sh](lint.sh).

Properties of the current lint pipeline:

- enumerates maintained Python files under the primary source trees
- runs pylint through the selected interpreter
- enforces `--fail-under=10`

Command:

```bash
bash ./lint.sh
```

## CI Topology

Treat repeated integration failures as defects until evidence establishes an
intermittent cause. Keep the original JUnit failure alongside the single isolated
recheck. Retry transient downloads at the transfer boundary (three attempts for
connection interruptions or HTTP 429/5xx); do not increase whole-lifecycle retry
counts to hide startup crashes, missing libraries, or wrong query endpoints.
Readiness timeouts and unexpected shutdown failures must fail smoke tests too.
The shared smoke helpers retain query errors and capture runtime logs/doctor
output before cleanup can remove the failed server.

Smoke runners return 77 only for an explicit disabled module or unavailable
provider/owned-asset/host prerequisite. Setup errors, download failures, disk
exhaustion, readiness timeouts, and shutdown failures remain failures. CI and
`make smoke-test` display prerequisite skips separately from passes. The smoke
jobs also publish their result records to the job summary before uploading them.
Test artifact uploads retry once after a transfer/finalization error; the final
attempt and the required summary gate still fail if evidence is missing.

GoldSrc and Source smoke runners poll `info --json` for an A2S response before `query` and
`info`; a console marker alone does not prove protocol readiness. Source smoke
fixtures disable empty-server hibernation in their temporary config. Keep the
upstream Source wrapper when available, because it initializes the library search
path needed by the raw engine binary. Palworld uses its own dedicated-listener
message as the smoke readiness marker.

Valve launcher discovery tries the installation's own candidates before recursive
content matches; downloaded GMod mounts must not select a different game's
working directory. Custom executable overrides retain priority.

`runtime.read_server_logs(server, lines=None)` returns retained console output
without printing it, using the active process or Docker runtime. TeamSpeak uses
this to recover first-start ServerQuery credentials, caching them in an
exclusively created file with mode 0600 for subsequent container launches.
Authenticated `ts3` info, rather than TCP availability, gates readiness.
ServerQuery sends are spaced by 350ms, including login and quit. The initial
delay also separates sequential CLI sessions. This respects the default ten
commands per three seconds without changing the server's flood protection;
see the [TS3 exporter implementation notes](https://github.com/hikhvar/ts3exporter#channel-metrics).

Quake Live uses Steam A2S on its game port. Its `servercfg` directory selects
`fs_game`; `+exec` receives only the filename. Managed config entries use native
`set` syntax and `serverstartup` selects both map and factory. The factory
defaults to `ffa`, as illustrated in the [original id Software config](https://github.com/quakelive-server-standards/quakelive-server-standards/blob/master/configs/_id/server.cfg).
See also the [A2SQuery supported-game table](https://github.com/linKhehe/a2squery/blob/main/docs/source/index.rst#supported-games).

The integration readiness helpers use monotonic deadlines and stop early only
after two consistent doctor reports confirm the runtime has exited. Failed or
unknown Docker inspection results do not count as an exit. On failure, bounded
Docker diagnostics include exit/OOM state, process wait channels, stdin targets
and selected Steam log tails; existing redaction applies before logging.
Diagnostics also report bounded local TCP listeners and UDP bindings, plus
allowlisted numeric port arguments to check launcher forwarding. Other process
arguments and all environment values are excluded. Inaccessible Steam directories
are recorded as unavailable without aborting the remaining evidence collection.
Failed `send` commands collect the same bounded runtime evidence as failed start
commands, covering servers that exit before the readiness polling loop begins.

Classic Soldat uses the fixed file-server request for `logs/gamestat.txt` on TCP
game port + 10. The `soldat` query protocol requires the transfer terminator and
valid player-count/map fields, caps replies at 64 KiB, and bounds the whole
exchange by one monotonic deadline. It exposes no raw file or player-list data.
`solserver` synchronizes `[GAME] Logging` and `[NETWORK] Allow_Download` together
with its managed game settings; see the [maintained query implementation](https://github.com/gamedig/node-gamedig/blob/master/protocols/soldat.js).

ARK: Survival Ascended uses authenticated Source RCON `ListPlayers` for
readiness and information. ASA's old Steam query port is deprecated; declare
and publish the RCON TCP port and keep the admin password secret. ASA does not
reliably send Source's normal multipart terminator, so the query helper collects
fragments through a short quiet window while enforcing one overall deadline and
a 1 MiB response limit.

Modules can declare `port_claim_definitions` for auxiliary native listeners that
must be claimed in both process and Docker runtimes. A port definition's
`default` applies only when its datastore key is absent; an explicit `None`
continues to omit the mapping. Project CARS uses this to retain its native
Steam authentication port for older records without mutating their datastore.

For Source readiness failures, CI tries `query` and `info --json` before debugger
attachment. This separates a missing console marker from an unresponsive engine.
`ALPHAGSM_DIAGNOSTIC_IMAGE` enables native stack capture using the already-loaded
integration image (which includes GDB). A temporary container joins only the
target's PID namespace, has no network, uses a read-only root, drops all
capabilities except `SYS_PTRACE`, and keeps the default seccomp profile. The game
container's permissions remain unchanged. GDB skips initialization files,
auto-loading and debuginfod; it prints stack frames without arguments or locals.
Each attachment is limited to eight seconds, with at most two Source engine
processes and thirty seconds for the debugger container. Cleanup removes the
temporary container even after a Docker CLI timeout. Capture briefly pauses the
failed engine; native queries therefore happen first. Existing redaction also
applies to debugger output, and diagnostic failures never replace test failures.

The current Source investigation compares [run 34250522498](https://github.com/SectorAlpha/AlphaGSM/actions/runs/34250522498):
CSS and GMod process lifecycles passed; Docker still timed out after loading
Steam libraries. GMod's corrected cwd is `/srv/server`. The Docker snapshots
show a sleeping engine main thread and successful HTTP connectivity checks,
but neither proves whether Steam initialization is blocked or the engine is
running without the expected marker. Missing appinfo caches and early
`SteamAPI_Init` warnings are observations, not established causes. The next CI
capture must identify the waiting function and whether native A2S responds
before changing libraries, networking or runtime permissions.

Keep `ALPHAGSM_MINECRAFT_RELEASE_ID` and `ALPHAGSM_MINECRAFT_SERVER_URL`
paired and preserve them when switching the CI runner user. The shared Minecraft
fixture helper uses those pins without consulting the moving latest release;
a partial pin fails explicitly. This keeps the fixture aligned with the CI Java
runtime. Real integration/game/backend acceptance runs in CI for PR #36; local
validation uses unit tests and static checks.

The GitHub Actions workflow is [`.github/workflows/unittest.yaml`](.github/workflows/unittest.yaml).

The workflow runs for pull requests targeting `master`, scheduled coverage,
merge groups, manual dispatch and reusable release validation. Its current gates are:

- dependency/build setup, lint, unit tests, coverage, and standalone binary
  acceptance on Linux x86-64/ARM64, Windows x86-64, and macOS Intel/Apple Silicon
- change-classified, partitioned Linux game smoke and integration matrices,
  with separate standard and heavy lanes
- branch-local integration, Java, SteamCMD Linux, and Wine/Proton image builds
  used by the relevant lifecycle jobs
- backend process smoke/integration coverage plus backend Docker integration
- representative Minecraft backend integration on Windows and macOS

Ubuntu 24.04 is the full game-server lifecycle baseline. The Windows and macOS
jobs currently validate representative Minecraft backend paths only; broader
game-server lifecycle coverage on those platforms and on newer or other Linux
distributions remains future work.

ASTRONEER's dedicated server registers the address that players use rather
than a loopback or Docker bridge address. Its Docker smoke and integration
tests therefore run in the configurable heavy lane. Provision that runner
with an externally routable UDP endpoint, set
`ALPHAGSM_HEAVY_RUNNER_LABELS_JSON` to its runner label array, and set the
`ALPHAGSM_ASTRONEER_REGISTRATION_PUBLICIP` repository variable to the endpoint's
real IPv4 address. The endpoint must route the test's managed game port to the
runner. This setting is intentionally not used by AlphaGSM's local
process/Docker query resolver.

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
- `ALPHAGSM_GITHUB_TOKEN` for authenticated GitHub release metadata requests
- `ALPHAGSM_DEBUG`

The smoke tests rely on temporary config files and `ALPHAGSM_CONFIG_LOCATION` to isolate state per run.
GitHub Actions supplies `ALPHAGSM_GITHUB_TOKEN` to smoke and integration jobs
using the workflow's read-only `GITHUB_TOKEN`; local runs can omit it unless
they encounter GitHub's anonymous API rate limit.

Smoke, integration, and backend lifecycle tests must allocate game-port groups
through `scripts/select_test_port.py`. On Ubuntu 24.04 it reads
`/proc/sys/net/ipv4/ip_local_port_range` and excludes that whole range before
probing TCP and UDP availability inside the default `10000-29999` test pool.
Do not replace this with `bind(..., 0)`:
SteamCMD and other network-heavy setup commands can consume a kernel-selected
ephemeral source port between setup and start, causing a false live-listener
collision at AlphaGSM's strict port preflight.

Linux integration jobs run AlphaGSM inside a GitHub job container and launch
game-server containers through the mounted host Docker socket. The shared
runtime inspects the current container's bind mounts and rewrites source paths
back to host-visible locations before `docker run`. Container detection uses
the exported `HOSTNAME` when available and falls back to
`socket.gethostname()` because the non-root `su - gsmuser` login shell may
reset the environment variable.

The same job container exposes the host Actions tool cache at `/__t`.
Integration shards clear that unused cache before running the game matrix so
large SteamCMD payloads and branch-local runtime images can coexist on the
hosted runner disk. Keep that cleanup scoped to the integration jobs; build,
lint, unit, and coverage jobs may still need the tool cache.

The integration job image is built from the exact branch-local
`wine-proton` runtime image selected by the same workflow. Keep that base-image
dependency and build argument intact: Docker can then reuse the running job
container's Wine, prefix, Mono, and Proton layers when AlphaGSM launches a
Windows game-server container. Building those stacks independently can exhaust
the hosted runner after large SteamCMD installs.

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

## Standalone release contract

[`binary.yml`](.github/workflows/binary.yml) is reused by PR validation and the
release workflow. It builds Linux x86-64/ARM64, macOS Intel/Apple Silicon, and
Windows x86-64 executables with pinned runtime/build requirements. Each CI job
copies the executable into an isolated home outside the checkout, exercises
bundled manifests/templates, and drives a Minecraft lifecycle through separate
AlphaGSM commands, including console input and verified shutdown. Linux x86-64
also exercises the artifact with the branch-local Java Docker image. Integration
and real game acceptance for this PR run in CI; local validation uses unit tests,
lint, workflow checks, and builds.

The build collects package resources and dynamic imports together. Factorio's
placeholder implementation raises `NotImplementedError` at import and remains
excluded; a build must not imply unsupported code is enabled. Frozen processes
use the current executable for internal bulk-command dispatch, supervision and
Windows update workers, without invoking a sibling Python script. Never add a
runtime dependency on the source checkout or the build environment.

Tag publication waits for the complete validation workflow and signed-artifact
acceptance. Manual release dispatch validates and builds unsigned artifacts; it
does not publish. Linux artifacts receive checksums and GitHub build-provenance
attestations. Windows/macOS signing additionally requires these repository
secrets before a tagged release can succeed:

- `ALPHAGSM_WINDOWS_SIGN_PFX`, `ALPHAGSM_WINDOWS_SIGN_PASSWORD`: base64 PFX and
  password for Windows Authenticode signing.
- `ALPHAGSM_MACOS_SIGN_PFX`, `ALPHAGSM_MACOS_SIGN_PASSWORD`: base64 signing
  identity export and its password.
- `ALPHAGSM_CODESIGN_IDENTITY`: Developer ID Application identity passed into
  PyInstaller so nested Mach-O payloads are signed too.
- `ALPHAGSM_APPLE_ID`, `ALPHAGSM_APPLE_TEAM_ID`,
  `ALPHAGSM_APPLE_PASSWORD`: Apple notarization credentials.

Signing and notarization fail closed when credentials are absent or rejected.
No credentials were configured during this change's read-only repository check;
release certification remains an operator prerequisite. The ASTRONEER runner
variables described above were also absent. Do not invent substitute public IPs
or mark those jobs passed without the required provider environment.

Use `summarize-tests` as the stable required check in branch protection/merge
queue settings. It checks the exact expected artifact inventory and required
job outcomes, rejecting empty, missing, malformed or duplicate reports. Only
an initial test-failure exit code can be recovered by one matching successful
isolated recheck. The initial failure and its standard/heavy runner lane remain
visible. `FLAKY RECOVERED` is a temporary non-blocking classification, not proof
that a recurring failure has been fixed; track its failing node and log evidence.
Scheduled and merge-group runs exercise broad coverage beyond PR routing.

### State and process ownership

Local CLI commands acquire a per-server lock before constructing `Server`, so
load/mutate/save operations serialize across invocations. Interactive `connect`
does not retain that lock. Library callers that need a read-modify-write sequence
must use `JSONDataStore.transaction()`; a stale in-memory object followed by
`save()` alone cannot merge concurrent edits. `utils.state_io` owns portable
advisory locks and same-directory atomic writes. Persistent lock sidecars must
not be deleted during use because replacing an inode defeats ownership.

Public and secret datastore files retain their existing schema. A private
`.pending` journal makes a paired write recoverable after interruption; once the
journal is durable, recovery can finish the committed update even if the original
caller received an I/O error. This is not a general multi-server transaction.
`simple_kv_config` uses the same lock and atomic replacement for config edits.

The subprocess supervisor keeps an authenticated loopback endpoint, an owned
process group/job, and a bounded stdin queue. A successful send means queued for
delivery; a full queue fails explicitly. Windows Job Objects clean up descendants
when ownership ends. On Unix, an uncatchable supervisor death with a live orphan
retains diagnostic evidence and conservatively refuses a duplicate launch.
Docker `exec-console` uses a private FIFO and preserves attach input; custom
images using this console mode must supply `sh`, `mkfifo`, and `cat`. Existing
containers need an AlphaGSM stop/start to acquire the new launch wrapper.

### Capabilities and diagnostic evidence

`src/server/capabilities.py` is the shared view of runtime, provider, config-sync
and query declarations. `src/server/module_capabilities.json` is the generated
inventory consumed without importing game modules. Regenerate it with
`scripts/generate_module_parity_report.py`; do not infer operating-system or
architecture coverage when a module has no explicit evidence. Published support
states come from checked-in trackers and prerequisites, not the latest CI run.
They must not be presented as fresh cross-platform validation.

`doctor --json` emits schema version 1 with check IDs, categories, statuses,
runtime selection and capabilities. Failed checks return exit code 1; a stopped
server by itself is healthy. Diagnostic strings redact declared secret values,
sensitive argument values, credentials and URL query data. CI failure artifacts
contain reports and relevant log tails; operator-supplied game logs may still
contain information that the game itself chose to print.

Successful setup/update writes a private provenance record under
`DATAPATH/.provenance/<server>.installation.json`. It records available observed
Minecraft jar metadata/hashes and Steam build IDs; unsupported or unobservable
fields stay null. This records the installed payload and operation, not a full
server validation. Modules can expose `get_installation_provenance(server)` for
additional authoritative evidence through the shared recording path.

### Game-specific platform preflight

Modules can declare `process_platforms` and `process_architectures`, or implement
`get_platform_requirements(server)` when the selected version/build changes the
requirements. The hook returns metadata without downloading or changing state:

```python
def get_platform_requirements(server):
    return {
        "process": {"platforms": ["linux"], "architectures": ["x86_64"]},
        "docker": {"operating_system": "linux"},
    }
```

The process declarations describe the hosts on which this AlphaGSM integration
can run, including any explicitly supported wrapper. Existing
`supported_platforms`/`supported_architectures` are fallback declarations. Keep
these separate from host dependencies and provider/configuration checks, which
continue through their existing shared APIs. A missing declaration is unknown,
not a claim of support. TF2 now declares Linux process support because its
current installation/launcher uses `srcds_run` and Linux Steam client libraries;
this does not describe every upstream TF2 distribution.

`setup` and `update` check declared compatibility before installation. `start` checks it
before `prestart` and checks the final executable's ELF, PE, Mach-O or shebang
format immediately before launch. The launcher inspected is the one resolved in
the server's working directory. Explicit interpreter and Wine/Proton commands
can run their supported payloads; AlphaGSM does not silently add Wine, WSL or an
emulator. Undeclared CPU compatibility is not inferred from a successful format
check. Docker uses the daemon's reported OS, so a Windows desktop with a Linux
Docker daemon can run Linux containers. The six checked-in runtime families
require Linux containers; a custom image without an OS declaration stays unknown.

The generated capability inventory records normalized declarations, while
`doctor --json` reports the current host or daemon compatibility. Add module unit
coverage when introducing declarations and prove the supported lifecycle in CI.

The shared SteamCMD installation helper currently ships a Linux client and
rejects non-Linux hosts before creating directories or downloading. A Docker
game-runtime selection does not relocate the host install hook; use the Linux
manager container for this provisioning path on other desktop operating systems.

When upgrading an existing source environment that installed the obsolete
`crontab` distribution, remove that distribution with
`python -m pip uninstall crontab`, then install `requirements-runtime.txt` again.
AlphaGSM uses the `python-crontab` distribution's `CronTab` API. A fresh binary or
fresh environment does not need this cleanup.
