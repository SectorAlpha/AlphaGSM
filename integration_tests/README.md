# Integration Tests

This directory is reserved for slow, side-effectful tests that exercise real
downloads, installs, and process startup.

These tests are intentionally separate from the default `tests/` suite so the
normal unit test run stays fast and deterministic.

Run them with:

```bash
PYTHONPATH=. pytest integration_tests
```

The direct runner-style smoke checks live separately under `smoke_tests/`.

Run the Minecraft pytest integration test with:

```bash
ALPHAGSM_RUN_INTEGRATION=1 PYTHONPATH=. pytest integration_tests/test_minecraft_vanilla.py
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
