"""Integration test for mordserver."""

import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    default_runtime_backend,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)
from gamemodules.mordserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_mordserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    module_name = "mordserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itmordserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()
    query_host = detect_query_host()

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

        # Mordhau exposes a generic UDP listener on the game port in this environment.
        wait_for_info_protocol(env, server_name, "udp", 900)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server port is open" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Server port is open" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_generic_udp_closed(query_host, port, STOP_TIMEOUT)
