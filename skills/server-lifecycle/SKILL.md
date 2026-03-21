# Server Lifecycle

| Field | Value |
| --- | --- |
| Purpose | Preserve, document, and enforce the standard AlphaGSM server lifecycle contract. |
| Use when | Changing lifecycle code, adding a new game server, or documenting per-server behaviour. |
| Main source | `server/server.py`, `core/main.py`, and the relevant game module. |

| Field | Value |
| --- | --- |
| Inputs | Server dispatch logic, default command contract, and game module lifecycle code. |
| Outputs | Updated lifecycle code, matching docs, matching tests, and command-contract compliance for new modules. |
| Related files | `server/server.py`, `core/main.py`, `screen/screen.py`, `gamemodules/**`, `tests/server/*`. |

Use this skill when changing or documenting the lifecycle for a game server module, especially when adding a new game server type.

## Focus

Understand, preserve, and enforce this standard AlphaGSM flow:

1. `create`
2. optional `set`
3. `setup`
4. `start`
5. readiness verification
6. `status`
7. `message` if supported
8. `stop`
9. shutdown verification

## Standard Command Contract

New game server modules should fit into the standard AlphaGSM command model rather than inventing a separate workflow.

At minimum, a new server type should work correctly with the shared command surface for:

- `create`
- `setup`
- `start`
- `stop`
- `status`

Where applicable, it should also integrate cleanly with:

- `message`
- `backup`
- `connect`
- `dump`
- `set`

The goal is that a user can create and operate a new server type using the same AlphaGSM mental model they already use for Minecraft, TF2, or CS:GO.

## Test Expectations For New Server Types

When adding a new game server, treat the lifecycle work as incomplete until it has appropriate test coverage across the repository's test layers:

- unit tests for command parsing and module behaviour
- integration tests for end-to-end pytest coverage
- smoke tests for a streamed real-world lifecycle example

The smoke tests are not owned by this skill, but new server lifecycle work should still result in smoke coverage being added or updated.

## Files To Inspect

- `server/server.py`
- `core/main.py`
- `screen/screen.py`
- the relevant `gamemodules/...` file

## Update Rule

If lifecycle behaviour changes, update all relevant:

- integration tests
- smoke tests
- server guide docs
- `README.md`
- `DEVELOPERS.md`

If a new game server is added, verify that it participates in the standard command contract before treating it as complete.
