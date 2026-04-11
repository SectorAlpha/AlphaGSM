# Backend Integration Tests

End-to-end tests that run the AlphaGSM lifecycle
(**create -> setup -> start -> query -> info -> stop**) once per backend/runtime
path:

| Test file | Backend | Requires |
|-----------|---------|----------|
| `test_backend_screen.py` | GNU screen | `screen`, `java` |
| `test_backend_tmux.py` | tmux | `tmux`, `java` |
| `test_backend_subprocess.py` | subprocess (pure Python) | `java` |
| `test_backend_docker.py` | Docker runtime | `docker` |
| `test_backend_docker_manager.py` | AlphaGSM manager container driving Docker runtime | `docker` |
| `test_alphagsm_docker_wrapper.py` | `alphagsm-docker` wrapper | `docker`, Docker Compose |

## Docker runtime family coverage

Docker backend validation is now tracked by runtime family in
`backend_integration_tests/docker_family_matrix.py`.

Each runtime family now declares **three** representative Docker lifecycle
cases. CI currently runs the active Java cases:

- `java-minecraft-vanilla`
- `java-minecraft-paper`
- `java-minecraft-velocity`

The remaining declared families are tracked as planned activation work:

- `quake-linux`
- `service-console`
- `simple-tcp`
- `steamcmd-linux`
- `wine-proton`

## Running locally

```bash
ALPHAGSM_RUN_BACKEND_INTEGRATION=1 \
PYTHONPATH=src \
  python -m pytest backend_integration_tests/ -v
```

## CI

These run as dedicated host-runner jobs in the GitHub Actions workflow, in
parallel with the normal smoke and integration test matrix. A matching
**backend-smoke-test** job runs the bash-level smoke scripts under
`smoke_tests/run_backend_*.sh`.

The Linux backend job explicitly runs `test_backend_docker.py` against the
active matrix cases. That Docker step must prove the AlphaGSM command flow
itself: `create`, `setup`, `start`, readiness, `status`, `query`, `info`,
`info --json`, `stop`, and shutdown verification.

It also runs `test_backend_docker_manager.py`, which covers the optional
manager-container mode: AlphaGSM itself runs inside Docker, talks to the host
Docker socket, and launches a sibling Docker container for Minecraft.

The wrapper-level test file `test_alphagsm_docker_wrapper.py` now adds a
runtime-family probe matrix through `./alphagsm-docker`, proving that the
wrapper can create Docker-backed servers for each declared runtime family and
that local `query` / `info` checks can reach the published ports.

The Docker runtime checks intentionally do not run in the main
`integration-test` matrix, because that job is itself a GitHub Actions
`container:` job. AlphaGSM's Docker runtime needs access to a real Docker
daemon, so the Docker smoke/integration coverage runs in the host-runner
backend jobs instead.

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
