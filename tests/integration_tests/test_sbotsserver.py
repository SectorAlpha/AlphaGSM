"""Integration test for sbotsserver."""

import json
import os

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    log_command_result,
    pick_free_udp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)
from gamemodules.sbotsserver import steam_app_id


pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_sbotsserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "sbotsserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itsbotsserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-SBOTS-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_port = pick_free_udp_port()
    while query_port == port:
        query_port = pick_free_udp_port()

    run_and_assert_ok(env, server_name, "create", module_name)

    setup_result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        setup_result,
    )
    if setup_result.returncode != 0:
        skip_for_known_steamcmd_issue(setup_result, app_id=steam_app_id)
    assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

    run_and_assert_ok(env, server_name, "set", "queryport", str(query_port))
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout
        assert str(query_port) in query_result.stdout

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "StickyBots Server" in info_result.stdout
        assert "Olympus" in info_result.stdout

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", info_data
        assert info_data["port"] == query_port, info_data
        assert info_data["game"] == "StickyBots", info_data
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
