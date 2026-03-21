# Server Lifecycle

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
