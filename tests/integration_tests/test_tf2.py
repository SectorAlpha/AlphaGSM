"""Integration test for Team Fortress 2."""

import json
import os
from pathlib import Path
import time

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_udp_closed,
)
from gamemodules.teamfortress2 import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

TEST_TIMEOUT_SECONDS = 1200
START_TIMEOUT_SECONDS = 600
STOP_TIMEOUT_SECONDS = 90
READY_LOG_MARKERS = ("SV_ActivateServer: setting tickrate")
HIBERNATION_MARKERS = ("Server is hibernating",)


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


def _assert_common_tf2_info(data, expected_map="cp_dustbowl"):
    assert data.get("players") == 0, f"Expected 0 players on fresh TF2 server: {data!r}"
    assert data.get("bots") == 0, f"Expected 0 bots on fresh TF2 server: {data!r}"
    assert data.get("map") == expected_map, f"Expected {expected_map} map: {data!r}"
    assert data.get("name") == "AlphaGSM TF2 Server", f"Unexpected TF2 name: {data!r}"


def test_tf2_download_install_and_start(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    module_name = "teamfortress2"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "tf2-server"
    config_path = tmp_path / "alphagsm-tf2.conf"
    port = pick_free_udp_port()
    server_name = f"ittf2{port % 100000:05d}"

    home_dir.mkdir()
    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-TF2-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    log_path = home_dir / "logs" / f"AlphaGSM-TF2-IT#{server_name}.log"
    query_host = detect_query_host()

    run_and_assert_ok(env, server_name, "create", module_name)
    setup_result = run_alphagsm(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=TEST_TIMEOUT_SECONDS,
    )
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        setup_result,
    )
    if setup_result.returncode != 0:
        skip_for_known_steamcmd_issue(setup_result, app_id=steam_app_id)
    _skip_for_known_tf2_setup_issue(setup_result)
    assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

    _assert_tf2_launcher_exists(install_dir)
    server_cfg_path = install_dir / "tf" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()

    installed_maps = sorted(
        path.stem for path in (install_dir / "tf" / "maps").glob("*.bsp")
    )
    assert installed_maps, "Expected TF2 install to expose at least one installed map"
    selected_map = installed_maps[0]

    describe_result = run_and_assert_ok(env, server_name, "set", "gamemap", "--describe")
    assert "Canonical key: map" in describe_result.stdout

    run_and_assert_ok(env, server_name, "set", "gamemap", selected_map)
    rcon_password = f"rcon-{port}"
    run_and_assert_ok(env, server_name, "set", "rconpassword", rcon_password)
    config_text = server_cfg_path.read_text(encoding="utf-8")
    assert f'rcon_password "{rcon_password}"' in config_text

    try:
        _set_tf2_hibernation(server_cfg_path, enabled=True)
        run_and_assert_ok(env, server_name, "start", timeout=60)
        wait_for_log_marker(log_path, READY_LOG_MARKERS, START_TIMEOUT_SECONDS)
        status_cmd = run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_cmd.stdout

        wait_for_log_marker(log_path, HIBERNATION_MARKERS, START_TIMEOUT_SECONDS)

        hibernating_info_result = run_and_assert_ok(
            env, server_name, "info", "--json"
        )
        hibernating_info = json.loads(hibernating_info_result.stdout.strip())
        assert hibernating_info["protocol"] in {"console", "a2s"}, (
            f"Expected console or a2s protocol for hibernating TF2: {hibernating_info!r}"
        )
        _assert_common_tf2_info(hibernating_info, expected_map=selected_map)
        if hibernating_info["protocol"] == "console":
            assert "version" in hibernating_info, (
                f"Expected console-derived version details for hibernating TF2: {hibernating_info!r}"
            )
            awake_info = _wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT_SECONDS)
        else:
            awake_info = hibernating_info

        _assert_common_tf2_info(awake_info, expected_map=selected_map)
        assert "Team Fortress" in (awake_info.get("game") or ""), (
            f"Expected 'Team Fortress' in game field: {awake_info!r}"
        )

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        print("\n=== query ===")
        print(query_result.stdout.strip())
        assert "Server is responding" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        print("\n=== info (awake) ===")
        print(info_result.stdout.strip())
        assert "Server info (A2S" in info_result.stdout, (
            f"Expected A2S info output from TF2: {info_result.stdout!r}"
        )

        # info --json — verify structured JSON output
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol for TF2: {_info_data!r}"
        )
        _assert_common_tf2_info(_info_data, expected_map=selected_map)
        assert "Team Fortress" in (_info_data.get("game") or ""), (
            f"Expected 'Team Fortress' in game field: {_info_data!r}"
        )
    finally:
        log_command_result(
            "alphagsm stop",
            run_alphagsm(env, server_name, "stop", timeout=STOP_TIMEOUT_SECONDS),
        )
        wait_for_udp_closed(query_host, port, STOP_TIMEOUT_SECONDS)
        final_status = run_and_assert_ok(env, server_name, "status")
        assert "isn't running" in final_status.stdout
