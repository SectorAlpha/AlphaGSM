"""Integration test for terraria.vanilla."""

import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_open,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_terraria_vanilla_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itterrariavani"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "terraria.vanilla")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["Listening on port", "Type 'help'"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # Vanilla Terraria uses TCP only; wait for the port to accept connections
        wait_for_tcp_open("127.0.0.1", port, 300, log_path=log_path)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert any(
            marker in query_result.stdout
            for marker in ("Server is responding", "Server port is open")
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Server port is open" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json — vanilla Terraria falls back to TCP (no A2S support)
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
