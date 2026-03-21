# Server Lifecycle

| Field | Value |
| --- | --- |
| Purpose | Preserve and document the real AlphaGSM server lifecycle. |
| Use when | Changing lifecycle code or documenting per-server behaviour. |
| Main source | `smoke_tests/`, `server/server.py`, and the relevant game module. |

| Field | Value |
| --- | --- |
| Inputs | Smoke tests, integration tests, server dispatch logic, game module lifecycle code. |
| Outputs | Updated lifecycle code, matching docs, and matching tests. |
| Related files | `server/server.py`, `core/main.py`, `screen/screen.py`, `smoke_tests/*.sh`, `integration_tests/*`, `gamemodules/**`. |

Use this skill when changing or documenting the lifecycle for a game server module.

## Focus

Understand and preserve this flow:

1. `create`
2. optional `set`
3. `setup`
4. `start`
5. readiness verification
6. `status`
7. `message` if supported
8. `stop`
9. shutdown verification

## Files To Inspect

- `server/server.py`
- `core/main.py`
- `screen/screen.py`
- `smoke_tests/*.sh`
- the relevant `gamemodules/...` file

## Update Rule

If lifecycle behaviour changes, update all relevant:

- smoke tests
- integration tests
- server guide docs
- `README.md`
- `DEVELOPERS.md`
