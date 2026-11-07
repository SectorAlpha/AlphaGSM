"""Integration test for qwserver."""

import os
import sys

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_qwserver_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "qwserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itqwserver"

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
    log_command_result("alphagsm setup", result)
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)
    assert result.returncode == 0, result.stderr or result.stdout

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # status
        run_and_assert_ok(env, server_name, "status")

        wait_for_info_protocol(env, server_name, "quakeworld", START_TIMEOUT, expected_port=port)

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
        assert _info_data["protocol"] == "quakeworld", (
            f"Expected quakeworld protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)

    # verify stopped
    wait_for_generic_udp_closed(
        "127.0.0.1", port, STOP_TIMEOUT, payload=b"\xff\xff\xff\xffstatus\n"
    )
