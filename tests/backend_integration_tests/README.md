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

## Windows Docker Integration Test

See `Dockerfile.windows` for a sample Windows container setup with Java and Python.

To run the Minecraft Vanilla subprocess backend integration test in a Windows container:

1. Build the image:
   ```powershell
   docker build -f backend_integration_tests/Dockerfile.windows -t alphagsm-win .
   ```
2. Run the container interactively:
   ```powershell
   docker run --rm -it alphagsm-win powershell
   # Inside the container, set up Python and Java as needed, then run:
   cd C:\alphagsm
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   # Download Minecraft server jar, then run the subprocess backend test manually.
   ```
3. The test `test_minecraft_windows_container.py` is a placeholder/skipped unless on Windows. Adapt it for full automation as needed.

**Note:** Windows containers require a Windows host. This test will be skipped on Linux.
