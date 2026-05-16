"""Integration test for ns2cserver."""

import json

import pytest

from conftest import (
    alphagsm_env,
    log_command_result,
    pick_free_tcp_port,
    require_command,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)
from gamemodules.ns2cserver import steam_app_id


pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_ns2cserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itns2cserver"

    write_config(config_path, home_dir, session_tag="AlphaGSM-NS2C-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    run_and_assert_ok(env, server_name, "create", "ns2cserver")

    setup_result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        setup_result,
    )
    if setup_result.returncode != 0:
        skip_for_known_steamcmd_issue(setup_result, app_id=steam_app_id)
    assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

    assert (install_dir / server_name).is_dir()
    assert (install_dir / server_name / "Workshop").is_dir()
    assert (install_dir / "ia32" / "ns2combatserver_linux32").exists()

    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Protocol" in info_result.stdout

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", info_data
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)