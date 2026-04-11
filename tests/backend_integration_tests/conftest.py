"""Shared fixtures for backend integration tests.

These tests run the AlphaGSM lifecycle across supported process backends and
the Docker runtime path. Active Docker cases are declared in
``docker_family_matrix.py`` and must prove ``create -> setup -> start ->
query -> info -> stop`` through AlphaGSM itself.
"""

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
STATUS_HELPER = REPO_ROOT / "tests" / "smoke_tests" / "minecraft_status.py"

BACKEND_TEST_TIMEOUT = 1200  # 20 minutes per test


# ---------------------------------------------------------------------------
# Override global network blocker
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _block_network():
    """No-op override: backend integration tests need real network access."""


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Increase the timeout for every backend-integration test."""
    for item in items:
        item.add_marker(pytest.mark.timeout(BACKEND_TEST_TIMEOUT))


# ---------------------------------------------------------------------------
# Helpers (used by the lifecycle fixture below)
# ---------------------------------------------------------------------------

def _require_backend_opt_in():
    if os.environ.get("ALPHAGSM_RUN_BACKEND_INTEGRATION") != "1":
        pytest.skip(
            "Set ALPHAGSM_RUN_BACKEND_INTEGRATION=1 to run backend integration tests"
        )


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _pick_free_tcp_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _latest_minecraft_release():
    result = subprocess.run(
        [sys.executable, str(STATUS_HELPER), "latest-release"],
        capture_output=True, text=True, check=True, timeout=60,
    )
    parts = result.stdout.strip().split("\t")
    return parts[0], parts[1]
def _write_config(
    config_path,
    home_dir,
    session_tag,
    backend,
    runtime_backend="process",
    servermodulespackage="gamemodules.",
):
    config_path.write_text(
        "\n".join([
            "[core]",
            f"alphagsm_path = {home_dir}",
            f"userconf = {home_dir}",
            "",
            "[downloader]",
            f"db_path = {home_dir / 'downloads' / 'downloads.txt'}",
            f"target_path = {home_dir / 'downloads' / 'downloads'}",
            "",
            "[server]",
            f"datapath = {home_dir / 'conf'}",
            f"servermodulespackage = {servermodulespackage}",
            "",
            "[screen]",
            f"screenlog_path = {home_dir / 'logs'}",
            f"sessiontag = {session_tag}",
            "keeplogs = 1",
            "",
            "[runtime]",
            f"backend = {runtime_backend}",
            "",
            "[process]",
            f"backend = {backend}",
            "",
        ]) + "\n"
    )


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(REPO_ROOT),
            str(REPO_ROOT / "src"),
        ]
    )
    return env


def _server_data_path(home_dir, server_name):
    return home_dir / "conf" / f"{server_name}.json"


def _load_server_data(home_dir, server_name):
    return json.loads(_server_data_path(home_dir, server_name).read_text(encoding="utf-8"))


def _run_alphagsm(env, *args, timeout=BACKEND_TEST_TIMEOUT):
    command = [sys.executable, str(ALPHAGSM_SCRIPT)] + list(args)
    return subprocess.run(
        command,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _ensure_docker_image(image):
    inspect = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=60,
    )
    if inspect.returncode == 0:
        return
    pull = subprocess.run(
        ["docker", "pull", image],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=900,
    )
    _log_command_result("docker pull " + image, pull)
    if pull.returncode != 0:
        pytest.fail("Required Docker image could not be pulled: " + image)


def _log_command_result(label, result):
    print(f"\n=== {label} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:", result.stdout.rstrip())
    if result.stderr:
        print("stderr:", result.stderr.rstrip())


def _bind_tcp_listener(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    sock.listen(5)
    return sock


def _run_and_assert_ok(env, *args, timeout=BACKEND_TEST_TIMEOUT):
    result = _run_alphagsm(env, *args, timeout=timeout)
    _log_command_result("alphagsm " + " ".join(args), result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _wait_for_status(host, port, timeout_seconds):
    result = subprocess.run(
        [
            sys.executable, str(STATUS_HELPER),
            "wait-for-status", host, str(port), str(timeout_seconds),
        ],
        capture_output=True, text=True, timeout=timeout_seconds + 30, check=False,
    )
    if result.returncode != 0:
        _log_command_result("wait-for-status", result)
        pytest.fail(
            f"Minecraft status did not respond within {timeout_seconds}s"
        )


def _wait_for_closed(host, port, timeout_seconds):
    result = subprocess.run(
        [
            sys.executable, str(STATUS_HELPER),
            "wait-for-closed", host, str(port), str(timeout_seconds),
        ],
        capture_output=True, text=True, timeout=timeout_seconds + 30, check=False,
    )
    _log_command_result("wait-for-closed", result)
    if result.returncode != 0:
        pytest.fail(
            f"Service on {host}:{port} did not stop within {timeout_seconds}s"
        )


def _wait_for_tcp_open(host, port, timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    last_error = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.2)
    pytest.fail(
        f"Service on {host}:{port} did not open within {timeout_seconds}s"
        + (f" ({last_error})" if last_error is not None else "")
    )


# ---------------------------------------------------------------------------
# Public fixture: minecraft_backend_lifecycle
# ---------------------------------------------------------------------------

class BackendLifecycle:
    """Bundles all helpers so tests call self.<method> without imports."""

    require_backend_opt_in = staticmethod(_require_backend_opt_in)
    require_command = staticmethod(_require_command)
    pick_free_tcp_port = staticmethod(_pick_free_tcp_port)
    latest_minecraft_release = staticmethod(_latest_minecraft_release)
    write_config = staticmethod(_write_config)
    alphagsm_env = staticmethod(_alphagsm_env)
    server_data_path = staticmethod(_server_data_path)
    load_server_data = staticmethod(_load_server_data)
    run_alphagsm = staticmethod(_run_alphagsm)
    run_and_assert_ok = staticmethod(_run_and_assert_ok)
    ensure_docker_image = staticmethod(_ensure_docker_image)
    log_command_result = staticmethod(_log_command_result)
    bind_tcp_listener = staticmethod(_bind_tcp_listener)
    wait_for_status = staticmethod(_wait_for_status)
    wait_for_closed = staticmethod(_wait_for_closed)
    wait_for_tcp_open = staticmethod(_wait_for_tcp_open)


@pytest.fixture()
def lifecycle():
    """Provide a helper bundle for backend lifecycle tests."""
    return BackendLifecycle()
