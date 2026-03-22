"""Integration test for primalcarnageextinctionserver."""

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
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 300
STOP_TIMEOUT = 90


def test_primalcarnageextinctionserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itprimalcarnag"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "primalcarnageextinctionserver")

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
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")
    finally:
        # stop
        run_and_assert_ok(env, server_name, "stop")

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
