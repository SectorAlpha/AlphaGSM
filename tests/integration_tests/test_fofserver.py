"""Integration test for fofserver."""

import json

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    read_info_json,
    find_source_server_cfg,
    set_source_hibernation,
    assert_source_server_empty,
    wait_for_log_marker,
    wait_for_a2s_ready,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.fofserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_fofserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itfofserver"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_host = detect_query_host()

    # create
    run_and_assert_ok(env, server_name, "create", "fofserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    server_cfg_path = find_source_server_cfg(install_dir)
    set_source_hibernation(server_cfg_path, enabled=True)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["SV_ActivateServer", "ready"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        hibernating_info = read_info_json(env, server_name)
        assert hibernating_info["protocol"] in {"console", "a2s"}, (
            f"Expected console or a2s info after startup: {hibernating_info!r}"
        )
        assert_source_server_empty(hibernating_info)

        if hibernating_info["protocol"] != "a2s":
            awake_info = wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)
            assert_source_server_empty(awake_info)

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

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert_source_server_empty(_info_data)
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
