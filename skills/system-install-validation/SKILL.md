# System Install Validation

| Field | Value |
| --- | --- |
| Purpose | Verify that a server install is runnable on the current host, not just downloaded to disk. |
| Use when | Debugging setup/start failures, missing runtimes, bad permissions, missing shared libraries, or CI-only environment issues. |
| Main source | The game module's install/start logic, smoke tests, integration tests, and the installed server directory. |

| Field | Value |
| --- | --- |
| Inputs | Installed files, expected executable, runtime/toolchain requirements, and startup/query diagnostics. |
| Outputs | A validated host/runtime checklist, clearer failure diagnosis, and fixes to either the module or the test environment. |
| Related files | `src/gamemodules/**`, `tests/integration_tests/conftest.py`, `tests/smoke_tests/*.sh`, `disabled_servers.conf`, `AGENTS.md`. |

Use this skill when a server appears "installed" but still cannot actually start, answer queries, or complete the lifecycle in CI.

## Validation Order

1. Confirm the expected executable exists at the path returned by `get_start_command()`.
2. Confirm it is runnable on this host: execute bit, shebang/interpreter, and any obvious shared-library/runtime dependencies.
3. Start the server with the real AlphaGSM command path, not a hand-built shortcut.
4. Wait for the correct readiness signal: log marker first, then the protocol-specific network helper.
5. Verify `status`, `query`, and `info` with the exact protocol the module declares.

## Typical Host Dependencies

- `screen` for the normal AlphaGSM lifecycle
- SteamCMD and any required authentication for Steam-distributed servers
- Java for Minecraft-family servers
- Wine/Proton or Mono for Windows-targeted dedicated servers
- Build tools only when the module truly compiles from source

## Failure Policy

- A query timeout is a real defect to diagnose, not something to hide with a skip.
- If the server needs more startup time, increase the timeout in the test and document why.
- Only use `disabled_servers.conf` when the server genuinely cannot run in CI at all.
- If the host is missing a prerequisite, fix the environment expectation or document the unsupported case explicitly.
- Before disabling a server, search the web for the upstream server's required
  config files, launch flags, authentication requirements, runtime packages,
  shared libraries, and Wine/Proton guidance. Prioritise official docs and
  upstream issue trackers.

## Enablement Mindset

- The goal is to keep as many servers enabled as possible.
- A server counts as enabled only when its integration test passes.
- A failing integration test means there is more validation or implementation
  work to do, not that the module should automatically stay disabled.

## Good Evidence To Capture

- The server log tail printed by the integration helpers
- The exact executable and working directory from `get_start_command()`
- The protocol hook returned by `get_query_address()` / `get_info_address()`
- Whether the failure is install-time, startup-time, or query-time
