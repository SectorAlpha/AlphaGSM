"""Integration test for l4d2server."""

import json
import os

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
    wait_for_info_protocol,
    set_source_hibernation,
    wait_for_runtime_log_marker,
    wait_for_a2s_ready,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.l4d2server import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _assert_common_l4d2_info(data):
    assert data.get("players") == 0, f"Expected 0 players on fresh server: {data!r}"
    assert data.get("bots") == 0, f"Expected 0 bots on fresh server: {data!r}"
    assert data.get("map") == "c5m1_waterfront", f"Expected c5m1_waterfront map: {data!r}"
    assert data.get("name") == "AlphaGSM Left 4 Dead 2", f"Unexpected L4D2 name: {data!r}"


def test_l4d2server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    module_name = "l4d2server"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itl4d2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_host = detect_query_host()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        result,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    assert result.returncode == 0, f"setup failed: {result.stderr or result.stdout}"

    server_cfg_path = install_dir / "left4dead2" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()
    set_source_hibernation(server_cfg_path, enabled=False)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["SV_ActivateServer", "Connection to Steam servers successful", "VAC secure mode"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        _assert_common_l4d2_info(info_data)

        wait_for_a2s_ready(query_host, port, 600, log_path=log_path)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players     : 0/" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == port, (
            f"Expected A2S query port {port}: {_info_data!r}"
        )
        _assert_common_l4d2_info(_info_data)
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
