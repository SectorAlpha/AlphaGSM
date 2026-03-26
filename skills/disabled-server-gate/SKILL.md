# Disabled Server Gate

| Field | Value |
| --- | --- |
| Purpose | Block creation of game servers whose modules are known-broken, with a clear reason and a request for help. |
| Use when | Disabling a server module, re-enabling a fixed module, or debugging why `create` is rejected. |
| Main source | `disabled_servers.conf` at the project root, `server/server.py` `_findmodule()`. |

| Field | Value |
| --- | --- |
| Inputs | The module name the user passes to `create`, the `disabled_servers.conf` file. |
| Outputs | A `ServerError` with the reason and a request to open an issue or submit a PR. |
| Related files | `disabled_servers.conf`, `src/server/server.py`, `src/core/main.py`, `tests/integration_tests/`. |

Use this skill when disabling or re-enabling a game server module, or when investigating why a `create` command is being refused.

## How It Works

1. The user runs `alphagsm myserver create bf1942server`.
2. `Server.__init__()` calls `_findmodule("bf1942server")`.
3. `_findmodule()` loads `disabled_servers.conf` and checks every name it encounters during alias resolution.
4. If the name appears in the disabled list, a `ServerError` is raised with the reason and a help message.
5. `core/main.py` catches the error and prints it.

The check runs inside the alias-resolution loop, so it catches both the original user-supplied name and any intermediate alias target.

## The Disabled Servers File

Location: `disabled_servers.conf` (project root).

Format:

```
# Comments start with #
# Blank lines are ignored
# Each entry is tab-separated: module_name<TAB>reason
bf1942server	Download domain bf1942.lightcubed.com is dead
```

Rules:

- One module per line.
- Tab separates the module name from the reason.
- Comments (`#`) and blank lines are allowed.
- If no reason is given after the tab, the message says "No reason given".

## When To Disable A Server

Disable a server module when:

- Its download URL is permanently dead or returns 404/403.
- Its version scraper is broken and there is no quick fix.
- The upstream project has no release assets.
- The module requires a runtime or toolchain that cannot be auto-installed.

Do **not** disable a server just because:

- It needs SteamCMD (that is gated separately by the test opt-in flag).
- It needs authenticated SteamCMD login (handle with a skip in integration tests instead).
- It only works on a different OS (document the platform requirement in docs instead).

## When To Re-enable A Server

Remove or comment out the line in `disabled_servers.conf` once:

- The download URL is confirmed working again.
- The scraper or installer code has been fixed.
- An integration test passes for the server.

## Keeping Tests In Sync

When you disable a server module in `disabled_servers.conf`, also add a matching `pytest.mark.skip` to its integration test with a reason that matches. When you re-enable, remove the skip.

## Error Message

When a disabled module is requested, the user sees:

```
Can't create server
Server module 'bf1942server' is currently disabled: Download domain bf1942.lightcubed.com is dead
If you'd like to help fix this, please open an issue or submit a pull request.
```

## Key Code Locations

- `disabled_servers.conf` — the list itself
- `src/server/server.py` `_load_disabled_servers()` — parses the file
- `src/server/server.py` `_findmodule()` — checks each name during alias resolution
- `src/server/server.py` `_DISABLED_SERVERS_PATH` — resolves the file path relative to `server.py`
