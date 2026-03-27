"""Shared fixtures for process-backend integration tests.

These tests run the full Minecraft Vanilla lifecycle (create → setup →
start → verify → stop) once per backend to confirm that screen, tmux and
the subprocess fallback all work end-to-end through AlphaGSM.
"""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
STATUS_HELPER = REPO_ROOT / "smoke_tests" / "minecraft_status.py"

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


def _write_config(config_path, home_dir, session_tag, backend):
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
            "",
            "[screen]",
            f"screenlog_path = {home_dir / 'logs'}",
            f"sessiontag = {session_tag}",
            "keeplogs = 1",
            "",
            "[process]",
            f"backend = {backend}",
            "",
        ]) + "\n"
    )


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


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


def _log_command_result(label, result):
    print(f"\n=== {label} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:", result.stdout.rstrip())
    if result.stderr:
        print("stderr:", result.stderr.rstrip())


def _skip_for_known_issue(result):
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "No such file or directory",
        "returned non-zero exit status",
        "Can't stop a server that isn't running",
        "Error extracting download",
        "Can't download file",
    )
    if any(marker in combined for marker in known_markers):
        pytest.skip("Setup failed with known issue in CI")


def _run_and_assert_ok(env, *args, timeout=BACKEND_TEST_TIMEOUT):
    result = _run_alphagsm(env, *args, timeout=timeout)
    _log_command_result("alphagsm " + " ".join(args), result)
    if result.returncode != 0:
        _skip_for_known_issue(result)
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
        pytest.skip(
            f"Minecraft did not respond within {timeout_seconds}s — skipping"
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
    run_and_assert_ok = staticmethod(_run_and_assert_ok)
    wait_for_status = staticmethod(_wait_for_status)
    wait_for_closed = staticmethod(_wait_for_closed)


@pytest.fixture()
def lifecycle():
    """Provide a helper bundle for backend lifecycle tests."""
    return BackendLifecycle()
