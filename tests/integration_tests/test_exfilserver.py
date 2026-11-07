"""Integration test for exfilserver."""

import os
import sys

import pytest

from conftest import (
    default_runtime_backend,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_info_protocol,
    wait_for_udp_closed,
)
from gamemodules.exfilserver import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_exfilserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "exfilserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itexfilserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    queryport = pick_free_udp_port()
    while queryport == port:
        queryport = pick_free_udp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_runtime_log_marker(
            env,
            server_name,
            (f"IpNetDriver listening on port {port}",),
            START_TIMEOUT,
        )
        info_data = wait_for_info_protocol(
            env,
            server_name,
            "a2s",
            START_TIMEOUT,
            expected_port=queryport,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "A2S on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "A2S" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == queryport, (
            f"Expected the Steam query port in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", queryport, STOP_TIMEOUT)
