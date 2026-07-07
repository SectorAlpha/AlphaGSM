"""Integration test for btlserver."""

import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port_group,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.btlserver import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_btlserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "btlserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itbtlserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
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
            "Players     : 0/" in info_result.stdout
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
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
