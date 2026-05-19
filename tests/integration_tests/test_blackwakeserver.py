"""Integration test for blackwakeserver."""

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    require_proton,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_blackwakeserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_proton()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itblackwakeser"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "blackwakeserver")

    # setup
    _setup_result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
    )

    # start
    run_and_assert_ok(env, server_name, "start")
    query_port = None

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

        # Use the module-owned query path instead of assuming the default query port.
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

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
        query_port = int(_info_data["port"])
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
    if query_port is not None:
        wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
