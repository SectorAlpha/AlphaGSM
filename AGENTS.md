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
4. If the server genuinely needs more time (e.g. large SteamCMD download),
   raise the timeout in the test rather than disabling the server.
5. `disabled_servers.conf` is only for servers that **cannot** run in CI at
   all (requires auth, dead download URL, known broken binary, etc.).

The wait helpers in `tests/integration_tests/conftest.py` print the last 150
lines of the server log and the last query error before calling
`pytest.skip()`. Use that output to understand what actually happened.

## Known Exception

`src/downloadermodules/steamcmd.py` is legacy parser-broken code and is intentionally outside the active lint/docstring verification surface.

## Repo Skills

See:

- `SKILLS.md`
- `skills/disabled-server-gate/SKILL.md`
- `skills/install-layout/SKILL.md`
- `skills/server-info-gathering/SKILL.md`
- `skills/server-lifecycle/SKILL.md`
- `skills/smoke-driven-docs/SKILL.md`
- `skills/system-install-validation/SKILL.md`
- `skills/wiki-publishing/SKILL.md`
