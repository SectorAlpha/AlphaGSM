# Adding A Game Server

This page is for two audiences:

- **Operators and new contributors** who want the short path: copy a similar
  game, keep the same commands, and land a working lifecycle.
- **Module authors** who need the exact AlphaGSM contract, tests, and docs.

You do not add a game by editing a config file. Each game is a **module**: a
Python package under `src/gamemodules/<name>/` that AlphaGSM loads by name.

```text
create → setup → start → status / query / info → stop
```

That is the same operator flow as Minecraft, TF2, Palworld, and HL2DM. A new
module is incomplete until it participates in that flow.

## Pick a similar working example

| If the dedicated server is… | Start from | Why |
| --- | --- | --- |
| A Linux SteamCMD app with its own layout | [Palworld](servers/palworld.md) (`src/gamemodules/palworld/`) | Custom install: reusable SteamCMD download, then game-specific settings |
| Source / GoldSrc with `srcds_run` | [HL2DM](servers/hl2dmserver.md) (`src/gamemodules/hl2dmserver/`) | Family builder plus explicit Docker ports |
| A Java jar | [Minecraft Vanilla](servers/minecraft-vanilla.md) (`src/gamemodules/minecraft/vanilla.py`) | Java runtime family |
| Another Valve game | `src/utils/valve_server.py` via `define_valve_server_module()` | Shared Source/GoldSrc defaults |

Copy the closest module. Do not invent a new command language.

## Operator-shaped outcome

When the module is done, this should work with the same commands users already
know:

```bash
./alphagsm myserver create <module_id>
./alphagsm myserver setup
./alphagsm myserver start
./alphagsm myserver status
./alphagsm myserver query
./alphagsm myserver info
./alphagsm myserver info --json
./alphagsm myserver stop
```

If setup needs a port and install directory, the smoke tests pass them
non-interactively (`-n`, port, directory). Match that.

## Layout

Canonical top-level games are packages:

```text
src/gamemodules/<module_id>/
  __init__.py          # public import surface
  main.py              # lifecycle implementation
  curated_mods.json    # only if this game has its own checked-in mods
```

Keep the module id stable. `import_module("gamemodules.<module_id>")` is what
`create` uses. Aliases belong in `src/server/module_aliases.json`, not extra
wrapper files.

Flat `.py` helpers are fine **inside** an existing family (`minecraft/paper.py`).
Do not add a new top-level `src/gamemodules/mygame.py`.

## What the module must export

Required hooks (every module):

| Hook | Backs |
| --- | --- |
| `configure(server, ask, *args, **kwargs)` | `setup` — store at least `port` and `dir`, init backup, return `(args, kwargs)` for `install` |
| `install(server, *args, **kwargs)` | `setup` — download/copy files, write initial config |
| `get_start_command(server, *args, **kwargs)` | `start` — return `(argv_list, working_dir)` |
| `do_stop(server, time, *args, **kwargs)` | `stop` |
| `status`, `message`, `backup`, `checkvalue` | matching commands |
| `get_runtime_requirements(server)` | runtime / Docker metadata |
| `get_container_spec(server)` | Docker launch spec |

Also export `commands`, `command_args`, `command_descriptions`, and
`command_functions` (use `()` / `{}` when you have no extra commands).

Always add `get_info_address(server)` unless you use
`define_valve_server_module()`, which sets it. Add `get_query_address` when
the query port or protocol is not default A2S on the game port.

If `set` keys map to the game's own config file, add `sync_server_config(server)`
and list those keys in `config_sync_keys`. Do not put AlphaGSM-only keys
(backup, image, runtime metadata) in that list.

New modules should set:

```python
module_contract_version = 1
```

That opts the **public** import surface into structural validation before
runtime-hook inference. It proves hooks exist and are callable. It does **not**
prove the server starts, downloads, or authenticates.

The full hook specification is in [src/server/gamemodules.py](../src/server/gamemodules.py)
and [DEVELOPERS.md](../DEVELOPERS.md).

## Shared operations vs custom code

Ownership:

| Owner | Does |
| --- | --- |
| Manager (`Server`) | Command order, ports, datastore, runtime choice, errors |
| Shared operation | One action: SteamCMD download, a config rewrite, a runtime spec |
| Family builder | Defaults proven across an engine family |
| Game module | Order the operations, validate game values, handle exceptions |

Reuse a helper only when **success and failure behaviour** match. Palworld
calls `installers.download_steamcmd(...)` then prepares `PalWorldSettings.ini`
itself. HL2DM keeps `define_valve_server_module()` and declares
`RUNTIME_FAMILY` / `PORT_DEFINITIONS` once for both Docker wrappers.

Do not add a base-class hierarchy, mixin system, or game-name switches inside
shared helpers.

## Docker

Choose a runtime family first:

- `java`
- `quake-linux`
- `service-console`
- `simple-tcp`
- `steamcmd-linux`
- `wine-proton` (Windows-only on Linux)

Then write explicit module-scope wrappers:

```python
import server.runtime as runtime_module

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=PORT_DEFINITIONS,
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=PORT_DEFINITIONS,
    )
```

Keep `get_start_command` working for the host/process path as well.

## Tests (required)

A new module is not done until all of these exist:

1. **Unit tests** under `tests/unit_tests/` for module behaviour or hooks.
2. **One integration test** at `tests/integration_tests/test_<module>.py` that
   drives AlphaGSM commands — not the game binary directly:
   `create`, `setup`, `start`, readiness, `status`, `query`, `info`,
   `info --json`, `stop`, shutdown.
3. **A smoke runner** at `tests/smoke_tests/run_<module>.sh` showing the same
   real-world order.

For Source servers, hibernation is not a pass. The test must keep the server
awake enough that real A2S `query` / `info` succeed.

If the module is container-capable, prove the Docker path as well as process.

Quality gates:

```bash
make lint          # must score 10.00/10
make test
# integration/smoke in CI or with ALPHAGSM_WORK_DIR set; do not disable a
# server to hide a timeout
```

## Docs and tracker (same change)

- Add `docs/servers/<module_id>.md` with copy-paste create/setup/start/stop.
- Link it from [docs/README.md](README.md).
- Add a changelog entry.
- When integration actually passes, mark the server in [TEST_STATUS.md](TEST_STATUS.md)
  and regenerate [game-server-support.md](game-server-support.md). Do not promote
  support status from structural validation alone.

`PASSED` means the lifecycle self-provisions in CI.
`ENABLED (AUTH)` means provider credentials/tokens/licenses are still required.
`ENABLED (BYO)` means the operator must supply owned files, exports, or URLs.

## Checklist

- [ ] Package under `src/gamemodules/<module_id>/` with `__init__.py` + `main.py`
- [ ] Required hooks and command tables exported on the public surface
- [ ] `module_contract_version = 1`
- [ ] Explicit `get_runtime_requirements` / `get_container_spec`
- [ ] `get_info_address` (and `get_query_address` if needed)
- [ ] Config sync only for real game-config keys
- [ ] Unit test + AlphaGSM integration test + smoke runner
- [ ] Server guide, changelog, tracker update when the lifecycle is proven
