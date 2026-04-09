# AlphaGSM Agent Guide

This file is for coding agents and automation working inside this repository.

## Main Rule


Use the smoke tests as the most reliable example of how a server is supposed to be:

- created
- set up
- started
- checked
- stopped

Current smoke runners:

- `tests/smoke_tests/run_minecraft_vanilla.sh`
- `tests/smoke_tests/run_tf2.sh`

If code comments and docs disagree, check the smoke runners first.

## Documentation Split

Keep documentation split by audience:

- `README.md`
  simple, non-technical, copy-paste friendly
- `docs/`
  user-facing server guides
- `DEVELOPERS.md`
  technical, detailed, implementation-focused

## When Behaviour Changes

Update these in order when relevant:

1. the smoke test
2. the matching server guide
3. `README.md`
4. `DEVELOPERS.md`

## Quality Gates

- lint: `make lint` (or `bash ./lint.sh` directly) — must score `10.00/10`
- unit tests: `make test` — keep green
- integration tests: `make integration-test` (needs `ALPHAGSM_WORK_DIR` set) — keep green
- smoke tests: `make smoke-test` (or `make smoke-test SMOKE_TEST=run_<name>.sh`) — keep accurate

## New Module Test Contract

Every new game module is incomplete until it lands with:

- at least one unit test under `tests/unit_tests/` covering module behaviour
  or hooks
- one integration test under `tests/integration_tests/test_<module>.py`

The integration test must drive the lifecycle through **AlphaGSM commands**,
not by launching the binary directly. At minimum it must prove the ordered
AlphaGSM flow of `create`, `setup`, `start`, readiness, `query`, `info`, and
`stop`. In practice the canonical flow also includes `status`,
`info --json`, and explicit shutdown verification.

For Source-based servers, a hibernating server is **not** sufficient for new
module coverage. The integration path must keep the server awake enough that
`query` and `info` succeed via the real protocol rather than passing because
the log reached "Server is hibernating" or because TCP fallback happened to
work.

## Port Manager Contract

Port ownership is now part of the normal AlphaGSM lifecycle contract across
process and Docker runtimes.

- `set` must reject conflicting claim changes immediately, including primary
  ports, optional `*port` keys, hosted-IP keys like `bindaddress` /
  `publicip`, and claim-bearing runtime `ports` edits.
- `setup` may auto-shift the **whole claimed port set together** only for
  default-owned claims. Once a claim key is explicit, later setup runs must
  keep treating it as explicit until the user changes it again.
- `start` must hard-fail before `prestart(...)` if any claimed port is already
  owned by another AlphaGSM server or a live listener on the same hosted IP.
- Collision checks ignore protocol and include optional and runtime-published
  ports, not just the main game port.

## Container Runtime Contract

Container-capable modules should describe their runtime explicitly instead of
embedding Docker assumptions in ad hoc test code.

For repository maintenance, treat Docker run details as part of the baseline
game-module contract. When adding or editing a module, make sure the module
still provides Docker runtime metadata and a Docker launch spec through
explicit module-scope wrappers.

- Keep `get_start_command(...)` working for the traditional process runtime.
- Add `import server.runtime as runtime_module` in modules that use shared
  runtime builders.
- Add `get_runtime_requirements(server)` for Docker-capable modules.
- Add `get_container_spec(server)` with the image, command, env, mounts, and
  published ports needed to run the server in Docker.
- Choose the runtime family first, then delegate to `server.runtime` builders
  or `utils.proton` helpers inside the module wrappers.
- Do not merge a module change that drops Docker run details for that module.
- Keep the static runtime-contract coverage under
  `tests/unit_tests/test_runtime_contract_static.py` green.
- Keep `tests/backend_integration_tests/docker_family_matrix.py` at three
  declared representative cases per runtime family, and keep active cases
  green in CI via `tests/backend_integration_tests/test_backend_docker.py`.
- Prefer the shared runtime families now in use:
  - `java`
  - `quake-linux`
  - `service-console`
  - `simple-tcp`
  - `steamcmd-linux`
  - `wine-proton`
- Keep the matching image scaffolds under `docker/<family>/` aligned with the
  runtime family defaults in `src/server/runtime.py`.
- For Windows-only servers on Linux, prefer the shared `utils.proton`
  container helpers and the image scaffold under `docker/wine-proton/`
  instead of embedding ad hoc Wine/Proton Docker logic in each module.
- Update representative unit tests whenever a module's runtime wrappers change
  so the explicit Docker contract stays covered.

## Server Enablement Goal

Aim to keep as many server modules **enabled** as possible.

- A server is considered enabled only when its integration test passes.
- A failing integration test is a debugging task, not a reason to leave the
  server broken indefinitely.
- Before accepting a skip or disablement, search the web for the upstream
  server's required config, startup flags, tokens, runtime dependencies,
  package requirements, shared libraries, Wine/Proton notes, and known
  dedicated-server quirks.
- Prefer official documentation, vendor docs, release notes, and upstream
  issue trackers over forum guesswork when researching fixes.

## Integration Test Timeout Policy

Timeout-related skips in integration tests are **not acceptable** as a permanent
state. They indicate a real problem that must be diagnosed and fixed.

The wait helpers (`wait_for_log_marker`, `wait_for_a2s_ready`,
`wait_for_quake_ready`, `wait_for_tcp_open`) call `pytest.fail()` on timeout —
this surfaces as a red **FAILURE**, not a yellow skip. That is the intended
behaviour.

When a test fails due to timeout:

1. **Never** add the server to `disabled_servers.conf` to hide the failure.
2. Read the log tail printed by the `[diagnostic]` lines in the CI output.
3. Determine the root cause — download failure, startup crash, wrong readiness
   marker, or query port mismatch — and fix it.
4. Search the web for upstream documentation or issue reports that explain
   missing dependencies, required startup flags, config files, auth tokens, or
   engine/runtime prerequisites.
5. If the server genuinely needs more time (e.g. large SteamCMD download),
   raise the timeout in the test rather than disabling the server.
6. `disabled_servers.conf` is only for servers that **cannot** run in CI at
   all (requires auth, dead download URL, known broken binary, etc.).

The wait helpers in `tests/integration_tests/conftest.py` print the last 150
lines of the server log and the last query error before failing the test. Use
that output to understand what actually happened.

## Known Exception

`src/downloadermodules/steamcmd.py` is legacy parser-broken code and is intentionally outside the active lint/docstring verification surface.

## Repo Skills

See:

- `SKILLS.md`
- `skills/disabled-server-gate/SKILL.md`
- `skills/docker-runtime-wiring/SKILL.md`
- `skills/install-layout/SKILL.md`
- `skills/server-info-gathering/SKILL.md`
- `skills/server-lifecycle/SKILL.md`
- `skills/smoke-driven-docs/SKILL.md`
- `skills/system-install-validation/SKILL.md`
- `skills/wiki-publishing/SKILL.md`
