# Backend Integration Tests

End-to-end tests that run the full Minecraft Vanilla lifecycle
(**create → setup → start → verify → stop**) once per process backend:

| Test file | Backend | Requires |
|-----------|---------|----------|
| `test_backend_screen.py` | GNU screen | `screen`, `java` |
| `test_backend_tmux.py` | tmux | `tmux`, `java` |
| `test_backend_subprocess.py` | subprocess (pure Python) | `java` |

## Running locally

```bash
ALPHAGSM_RUN_BACKEND_INTEGRATION=1 \
PYTHONPATH=src \
  python -m pytest backend_integration_tests/ -v
```

## CI

These run as a dedicated **backend-integration-test** job in the GitHub
Actions workflow, in parallel with the normal smoke and integration test
matrix.  A matching **backend-smoke-test** job runs the bash-level smoke
scripts under `smoke_tests/run_backend_*.sh`.
