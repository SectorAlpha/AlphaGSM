"""Integration test for astroneerserver."""

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


def test_astroneerserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_proton()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itastroneerser"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "astroneerserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # Astroneer needs Windows RichEdit DLL (riched20); Wine may lack this.
        # Detect the Wine error early so the test skips quickly rather than
        # timing out after START_TIMEOUT seconds.
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        log_text = wait_for_log_marker(
            log_path,
            ["ready", "started", "listening", "Done", "err:richedit"],
            START_TIMEOUT,
        )
        if "err:richedit" in log_text:
            pytest.skip(
                "Astroneer server requires Windows RichEdit DLL (riched20) "
                "which is not available in the current Wine installation."
            )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        run_and_assert_ok(env, server_name, "query")
    finally:
        # stop
        run_and_assert_ok(env, server_name, "stop")

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
