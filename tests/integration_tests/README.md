# Integration Tests

This directory is reserved for slow, side-effectful tests that exercise real
downloads, installs, and process startup.

These tests are intentionally separate from the default `tests/` suite so the
normal unit test run stays fast and deterministic.

## Test Status

See [TEST_STATUS.md](../docs/TEST_STATUS.md) for the current pass/fail/skip/disabled
state of every integration test. Agents must update that file after each test
run.

Run them with:

```bash
PYTHONPATH=src pytest tests/integration_tests
```

The direct runner-style smoke checks live separately under `tests/smoke_tests/`.

Run the Minecraft pytest integration test with:

```bash
ALPHAGSM_RUN_INTEGRATION=1 PYTHONPATH=src pytest tests/integration_tests/test_minecraft_vanilla.py
```

Requirements for the Minecraft integration:

- outbound network access
- `java`
- `screen`

Current target:

- Vanilla Minecraft end-to-end setup through `alphagsm`:
  download the official server jar, install into a temporary directory, start
  the server under `screen`, ping it over the Minecraft status protocol, and
  stop it cleanly.
- Team Fortress 2 end-to-end setup through `alphagsm`:
  download the dedicated server via SteamCMD, start it, verify it responds to a
  Source query, and stop it cleanly.
- Archive-backed install flows through `alphagsm`:
  download and install real archive/release assets for modules like `etlegacyserver`
  and `cod2server`, then verify the expected server binaries land in the install
  directory.
