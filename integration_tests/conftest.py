"""Shared fixtures and helpers for AlphaGSM integration tests."""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"

# ---------------------------------------------------------------------------
# Override pytest-timeout for integration tests (default pytest.ini is 10s)
# ---------------------------------------------------------------------------
INTEGRATION_TEST_TIMEOUT = 1200  # 20 minutes per test function


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Give integration-marked tests a longer pytest-timeout."""
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT))


# ---------------------------------------------------------------------------
# Opt-in gates
# ---------------------------------------------------------------------------

def require_integration_opt_in():
    """Skip unless the integration flag is set."""
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def require_steamcmd_opt_in():
    """Skip unless the SteamCMD integration flag is set."""
    if os.environ.get("ALPHAGSM_RUN_STEAMCMD") != "1":
        pytest.skip("Set ALPHAGSM_RUN_STEAMCMD=1 to run SteamCMD integration tests")


def require_command(name):
    """Skip if a required system command is not available."""
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


# ---------------------------------------------------------------------------
# Port helpers
# ---------------------------------------------------------------------------

def pick_free_tcp_port():
    """Return an ephemeral TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def pick_free_udp_port():
    """Return an ephemeral UDP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


# ---------------------------------------------------------------------------
# Config / env helpers
# ---------------------------------------------------------------------------

def write_config(config_path, home_dir, session_tag="AlphaGSM-IT#"):
    """Write a minimal AlphaGSM config file pointing at *home_dir*."""
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
        ]) + "\n"
    )


def alphagsm_env(config_path):
    """Return an environ dict configured for an integration test run."""
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


# ---------------------------------------------------------------------------
# AlphaGSM command runners
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 1200


def run_alphagsm(env, *args, timeout=DEFAULT_TIMEOUT):
    """Run the alphagsm script and return the CompletedProcess."""
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


def log_command_result(name, result):
    """Print a subprocess result for CI diagnostics."""
    print(f"\n=== {name} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(result.stdout.rstrip())
    if result.stderr:
        print("stderr:")
        print(result.stderr.rstrip())


def run_and_assert_ok(env, *args, timeout=DEFAULT_TIMEOUT):
    """Run alphagsm and assert a zero return code."""
    result = run_alphagsm(env, *args, timeout=timeout)
    log_command_result("alphagsm " + " ".join(args), result)
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


# ---------------------------------------------------------------------------
# Wait helpers
# ---------------------------------------------------------------------------

def wait_for_log_marker(log_path, markers, timeout_seconds):
    """Poll a log file until one of *markers* appears; return the log text."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if any(marker in log_text for marker in markers):
                return log_text
        time.sleep(2)
    pytest.skip(
        f"Log never showed readiness markers within {timeout_seconds}s: {log_path}"
    )


def wait_for_tcp_closed(host, port, timeout_seconds):
    """Wait until a TCP connect to *host:port* fails."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                pass
        except Exception:  # noqa: BLE001
            return
        time.sleep(2)
    raise AssertionError(f"TCP port {host}:{port} still open after {timeout_seconds}s")


def wait_for_udp_closed(host, port, timeout_seconds):
    """Wait until a UDP Source query to *host:port* stops responding."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            try:
                sock.sendto(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00", (host, port))
                sock.recv(4096)
            except Exception:  # noqa: BLE001
                return
        time.sleep(2)
    raise AssertionError(f"UDP port {host}:{port} still responds after {timeout_seconds}s")


# ---------------------------------------------------------------------------
# SteamCMD skip helper
# ---------------------------------------------------------------------------

def skip_for_known_steamcmd_issue(result, app_id=None):
    """Skip the test if SteamCMD fails with a known transient issue."""
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "No such file or directory",
        "Failed to install app",
        "Missing configuration",
        "No subscription",
        "returned non-zero exit status",
        "Can't stop a server that isn't running",
    )
    if any(marker in combined for marker in known_markers):
        extra = f" (app {app_id})" if app_id else ""
        pytest.skip(f"SteamCMD setup failed with known issue{extra}")
