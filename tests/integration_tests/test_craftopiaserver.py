"""Integration test for craftopiaserver."""

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_udp_open,
    wait_for_udp_closed,
)
from gamemodules.craftopiaserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_craftopiaserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itcraftopiaser"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "craftopiaserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_udp_open("127.0.0.1", port, START_TIMEOUT, log_path=log_path)

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            f"Server port is open (UDP ping on port {port}" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            f"Server port is open (UDP ping on port {port}" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"
        assert "No further details available." in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, f"Unexpected info JSON: {_info_data!r}"
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
