"""Integration test for stormworksserver."""

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    require_proton,
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

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 300
STOP_TIMEOUT = 90


def test_stormworksserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")
    require_proton()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itstormworksse"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "stormworksserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # Stormworks app 1247090 is now a stub that prints a redirect message
        # ("dedicated server has been moved") and exits; the real server ships
        # with the purchased game.  Detect that message early so the test skips
        # in seconds rather than waiting out the full START_TIMEOUT.
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        log_text = wait_for_log_marker(
            log_path,
            ["ready", "started", "listening", "Done", "has been moved"],
            START_TIMEOUT,
        )
        if "has been moved" in log_text:
            pytest.skip(
                "Stormworks dedicated-server app (1247090) is now a redirect stub; "
                "the real server requires purchasing the game."
            )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
            or "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Server info" in info_result.stdout
            or "Server port is open" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"
    finally:
        # stop
        run_and_assert_ok(env, server_name, "stop")

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
