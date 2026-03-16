# Integration Tests

This directory is reserved for slow, side-effectful tests that exercise real
downloads, installs, and process startup.

These tests are intentionally separate from the default `tests/` suite so the
normal unit test run stays fast and deterministic.

Run them with:

```bash
PYTHONPATH=. pytest integration_tests
```

Or use the dedicated runner:

```bash
./run_integration_tests.sh
```

These tests are opt-in. For the Minecraft flow, enable:

```bash
ALPHAGSM_RUN_INTEGRATION=1 ./run_integration_tests.sh
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
