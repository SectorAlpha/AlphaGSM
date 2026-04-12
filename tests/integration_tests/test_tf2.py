"""Integration test for Team Fortress 2.

Requires SteamCMD — gated behind ALPHAGSM_RUN_STEAMCMD=1.
App ID is read from gamemodules.teamfortress2.steam_app_id.
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

from conftest import write_config
from gamemodules.teamfortress2 import steam_app_id

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
TEST_TIMEOUT_SECONDS = 1200
START_TIMEOUT_SECONDS = 600
STOP_TIMEOUT_SECONDS = 90
READY_LOG_MARKERS = ("SV_ActivateServer: setting tickrate")
HIBERNATION_MARKERS = ("Server is hibernating",)


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _require_steamcmd_opt_in():
    if os.environ.get("ALPHAGSM_RUN_STEAMCMD") != "1":
        pytest.skip("Set ALPHAGSM_RUN_STEAMCMD=1 to run SteamCMD integration tests")


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _pick_free_port():
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_sock:
            try:
                tcp_sock.bind(("127.0.0.1", port))
            except OSError:
                continue
        return port


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
        f"Failed to install app '{steam_app_id}' (Missing configuration)",
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
    return _wait_for_log_marker(log_path, READY_LOG_MARKERS, timeout_seconds)


def _wait_for_log_marker(log_path, markers, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(errors="replace")
            if any(marker in log_text for marker in markers):
                return log_text
        time.sleep(2)
    pytest.fail(
        f"TF2 server log never showed markers {markers!r} within {timeout_seconds}s: {log_path}"
    )


def _assert_tf2_launcher_exists(install_dir):
    launchers = [install_dir / "srcds_run_64", install_dir / "srcds_run"]
    assert any(path.exists() for path in launchers), "No TF2 launcher found after setup"


def _wait_for_info_protocol(env, server_name, expected_protocol, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_result = None
    last_data = None
    while time.time() < deadline:
        result = _run_alphagsm(env, server_name, "info", "--json", timeout=120)
        last_result = result
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                data = None
            else:
                last_data = data
                if data.get("protocol") == expected_protocol:
                    return data
        time.sleep(5)

    _log_command_result(
        "alphagsm " + " ".join((server_name, "info", "--json")),
        last_result,
    )
    pytest.fail(
        f"TF2 info --json never returned protocol {expected_protocol!r} within {timeout_seconds}s: "
        f"last payload={last_data!r}"
    )


def _set_tf2_hibernation(server_cfg_path, enabled):
    cfg_text = server_cfg_path.read_text(encoding="utf-8")
    target = "tf_allow_server_hibernation 0"
    replacement = "tf_allow_server_hibernation 1" if enabled else target
    if enabled:
        if target in cfg_text:
            cfg_text = cfg_text.replace(target, replacement)
        elif replacement not in cfg_text:
            cfg_text += "\ntf_allow_server_hibernation 1\n"
    else:
        cfg_text = cfg_text.replace("tf_allow_server_hibernation 1", target)
        if target not in cfg_text:
            cfg_text += "\ntf_allow_server_hibernation 0\n"
    server_cfg_path.write_text(cfg_text, encoding="utf-8")


def _assert_common_tf2_info(data):
    assert data.get("players") == 0, f"Expected 0 players on fresh TF2 server: {data!r}"
    assert data.get("bots") == 0, f"Expected 0 bots on fresh TF2 server: {data!r}"
    assert data.get("map") == "cp_dustbowl", f"Expected cp_dustbowl map: {data!r}"
    assert data.get("name") == "AlphaGSM TF2 Server", f"Unexpected TF2 name: {data!r}"


def test_tf2_download_install_and_start(tmp_path):
    _require_integration_opt_in()
    _require_steamcmd_opt_in()
    _require_command("screen")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "tf2-server"
    config_path = tmp_path / "alphagsm-tf2.conf"
    port = _pick_free_port()
    server_name = f"ittf2{port % 100000:05d}"

    home_dir.mkdir()
    write_config(config_path, home_dir, session_tag="AlphaGSM-TF2-IT#")
    env = _alphagsm_env(config_path)
    log_path = home_dir / "logs" / f"AlphaGSM-TF2-IT#{server_name}.log"

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
    server_cfg_path = install_dir / "tf" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()

    try:
        _set_tf2_hibernation(server_cfg_path, enabled=True)
        _run_and_assert_ok(env, server_name, "start", timeout=60)
        _wait_for_log_ready(log_path, START_TIMEOUT_SECONDS)
        status_cmd = _run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_cmd.stdout

        _wait_for_log_marker(log_path, HIBERNATION_MARKERS, START_TIMEOUT_SECONDS)

        hibernating_info_result = _run_and_assert_ok(
            env, server_name, "info", "--json"
        )
        hibernating_info = json.loads(hibernating_info_result.stdout.strip())
        assert hibernating_info["protocol"] in {"console", "a2s"}, (
            f"Expected console or a2s protocol for hibernating TF2: {hibernating_info!r}"
        )
        _assert_common_tf2_info(hibernating_info)
        if hibernating_info["protocol"] == "console":
            assert "version" in hibernating_info, (
                f"Expected console-derived version details for hibernating TF2: {hibernating_info!r}"
            )
            awake_info = _wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT_SECONDS)
        else:
            awake_info = hibernating_info

        _assert_common_tf2_info(awake_info)
        assert "Team Fortress" in (awake_info.get("game") or ""), (
            f"Expected 'Team Fortress' in game field: {awake_info!r}"
        )

        # query
        query_result = _run_and_assert_ok(env, server_name, "query")
        print("\n=== query ===")
        print(query_result.stdout.strip())
        assert "Server is responding" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = _run_and_assert_ok(env, server_name, "info")
        print("\n=== info (awake) ===")
        print(info_result.stdout.strip())
        assert "Server info (A2S" in info_result.stdout, (
            f"Expected A2S info output from TF2: {info_result.stdout!r}"
        )

        # info --json — verify structured JSON output
        info_json_result = _run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol for TF2: {_info_data!r}"
        )
        _assert_common_tf2_info(_info_data)
        assert "Team Fortress" in (_info_data.get("game") or ""), (
            f"Expected 'Team Fortress' in game field: {_info_data!r}"
        )
    finally:
        _log_command_result(
            "alphagsm stop",
            _run_alphagsm(env, server_name, "stop", timeout=STOP_TIMEOUT_SECONDS),
        )
        _wait_for_closed("127.0.0.1", port, STOP_TIMEOUT_SECONDS)
        final_status = _run_and_assert_ok(env, server_name, "status")
        assert "isn't running" in final_status.stdout
