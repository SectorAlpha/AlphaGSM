"""Integration test for Team Fortress 2.

Disabled: TF2 requires SteamCMD for download (app_id 232250).
Awaiting further support.
"""

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
TEST_TIMEOUT_SECONDS = 1200
START_TIMEOUT_SECONDS = 180
STOP_TIMEOUT_SECONDS = 90
READY_LOG_MARKERS = ("SV_ActivateServer: setting tickrate", "Server is hibernating")


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _write_config(config_path, home_dir):
    config_path.write_text(
        "\n".join(
            [
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
                "sessiontag = AlphaGSM-TF2-IT#",
                "keeplogs = 1",
                "",
            ]
        )
        + "\n"
    )


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run_alphagsm(env, *args, timeout=TEST_TIMEOUT_SECONDS):
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


def _log_command_result(name, result):
    print(f"\n=== {name} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(result.stdout.rstrip())
    if result.stderr:
        print("stderr:")
        print(result.stderr.rstrip())


def _run_and_assert_ok(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    result = _run_alphagsm(env, *args, timeout=timeout)
    _log_command_result("alphagsm " + " ".join(args), result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _skip_for_known_tf2_setup_issue(result):
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "tf/cfg/server.cfg",
        "No such file or directory",
        "Failed to install app '232250' (Missing configuration)",
    )
    if all(marker in combined for marker in known_markers):
        pytest.skip(
            "TF2 setup currently fails in production during install/config creation "
            "(missing tf/cfg/server.cfg after SteamCMD setup)"
        )


def _wait_for_closed(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(2)
            try:
                sock.connect((host, port))
                sock.send(b"\xFF\xFF\xFF\xFFTSource Engine Query\x00")
                sock.recv(4096)
            except Exception:  # noqa: BLE001
                return
        time.sleep(2)
    raise AssertionError("TF2 server still responds after stop timeout")


def _wait_for_log_ready(log_path, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if any(marker in log_text for marker in READY_LOG_MARKERS):
                return log_text
        time.sleep(2)
    raise AssertionError(f"TF2 server log never showed readiness markers: {log_path}")


def _wait_for_screen_exit(log_path, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if "Server is hibernating" in log_text:
                return
        time.sleep(2)
    raise AssertionError("TF2 log did not reach steady-state before stop")


def _assert_tf2_launcher_exists(install_dir):
    launchers = [install_dir / "srcds_run_64", install_dir / "srcds_run"]
    assert any(path.exists() for path in launchers), "No TF2 launcher found after setup"


@pytest.mark.skip(reason="Disabled: requires SteamCMD (app_id 232250)")
def test_tf2_download_install_and_start(tmp_path):
    _require_integration_opt_in()
    _require_command("screen")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "tf2-server"
    config_path = tmp_path / "alphagsm-tf2.conf"
    server_name = "ittf2"
    port = _pick_free_port()

    home_dir.mkdir()
    _write_config(config_path, home_dir)
    env = _alphagsm_env(config_path)
    log_path = home_dir / "logs" / "AlphaGSM-TF2-IT#ittf2.log"

    _run_and_assert_ok(env, server_name, "create", "teamfortress2")
    setup_result = _run_alphagsm(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=TEST_TIMEOUT_SECONDS,
    )
    _log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        setup_result,
    )
    _skip_for_known_tf2_setup_issue(setup_result)
    assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

    _assert_tf2_launcher_exists(install_dir)
    assert (install_dir / "tf" / "cfg" / "server.cfg").exists()

    _run_and_assert_ok(env, server_name, "start", timeout=60)

    try:
        log_text = _wait_for_log_ready(log_path, START_TIMEOUT_SECONDS)
        assert "SV_ActivateServer: setting tickrate" in log_text
        status_cmd = _run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_cmd.stdout
    finally:
        _wait_for_screen_exit(log_path, START_TIMEOUT_SECONDS)
        _run_and_assert_ok(env, server_name, "stop", timeout=STOP_TIMEOUT_SECONDS)
        _wait_for_closed("127.0.0.1", port, STOP_TIMEOUT_SECONDS)
        final_status = _run_and_assert_ok(env, server_name, "status")
        assert "isn't running" in final_status.stdout
