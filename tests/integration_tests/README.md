# Integration Tests

This directory is reserved for slow, side-effectful tests that exercise real
downloads, installs, and AlphaGSM-managed server startup.

These tests are intentionally separate from the default unit suite so normal
`tests/` runs stay fast and deterministic.

## Status Tracking

See [docs/TEST_STATUS.md](../../docs/TEST_STATUS.md) for the checked-in support
state of each server. Agents should keep that tracker aligned with what GitHub
CI has actually proven.

The direct runner-style smoke checks live separately under `tests/smoke_tests/`.

## Runtime Policy

Integration tests that consult `ALPHAGSM_TEST_RUNTIME_BACKEND` now default
through `default_runtime_backend()` in
[conftest.py](./conftest.py):

- local/default runs stay process-first
- GitHub Actions uses module-aware `auto`
- explicit `ALPHAGSM_TEST_RUNTIME_BACKEND=process|docker|auto` still overrides
  the default

That means repository integration tests can stay runtime-agnostic while GitHub
CI exercises Docker-capable modules through their declared runtime contracts.

## Running Locally

Run a specific test only when you actually intend to perform a real
download/install/start cycle:

```bash
ALPHAGSM_RUN_INTEGRATION=1 PYTHONPATH=src pytest tests/integration_tests/test_minecraft_vanilla.py
```

Or a whole subset:

```bash
ALPHAGSM_RUN_INTEGRATION=1 PYTHONPATH=src pytest tests/integration_tests
```

Many tests also require extra opt-ins such as SteamCMD auth, BYO archives, or
runtime-specific host tooling.

## CI-First Validation

For the current Docker-runtime enablement campaign, GitHub CI is the primary
proof surface for integration behavior. In particular:

- Docker-capable modules should be validated in GitHub Actions, not assumed
  from local process runs
- broad red batches should be triaged from workflow logs and uploaded test
  artifacts before changing contracts
- protocol-sensitive lanes like A2S should be treated as unresolved until
  GitHub CI proves them green under the intended runtime
- after the primary smoke, backend, and integration jobs finish, CI rechecks
  each failed integration node once on a fresh runner with the original
  `auto`, Docker, or process runtime selection
- a recovered recheck is reported as `FLAKY RECOVERED`, but the first failure
  remains release-blocking and is never overwritten by the recheck result

## Current Coverage Goals

- AlphaGSM lifecycle coverage through `create`, `setup`, `start`, readiness,
  `query`, `info`, and `stop`
- runtime-contract coverage for Docker-capable modules without baking
  process-versus-Docker branching into the test logic
- archive-backed, SteamCMD-backed, and BYO install flows staying truthful to
  the real supported environments
