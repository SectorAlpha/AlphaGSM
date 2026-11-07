"""Integration test for qlserver."""

import os
import sys

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    assert_alphagsm_result_ok,
    capture_alphagsm_stop,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)
from gamemodules.qlserver import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90

def test_qlserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "qlserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itqlserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result("alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))), result)
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    assert result.returncode == 0, result.stderr or result.stdout

    # start
    start_result = run_alphagsm(env, server_name, "start")
    log_command_result("alphagsm " + " ".join((server_name, "start")), start_result)
    if start_result.returncode != 0:
        skip_for_known_steamcmd_issue(start_result, app_id=steam_app_id)
    assert start_result.returncode == 0, start_result.stderr or start_result.stdout

    try:
        # wait for readiness
        wait_for_info_protocol(
            env,
            server_name,
            "a2s",
            START_TIMEOUT,
            expected_port=port,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    # verify stopped
    assert_alphagsm_result_ok(stop_result)
    wait_for_generic_udp_closed(
        "127.0.0.1", port, STOP_TIMEOUT, payload=b"\xff\xff\xff\xffTSource Engine Query\x00"
    )
    final_status = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in final_status.stdout
