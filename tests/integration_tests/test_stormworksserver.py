"""
Integration test for stormworksserver.

ENABLED (BYO): Stormworks requires authenticated Steam or SteamCMD access to
install the Dedicated Server tool; Steam app 1247090 is now only a redirect stub.
"""

import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): install the Stormworks Dedicated Server tool through logged-in Steam or authenticated SteamCMD, then stage that installed server tree into <install_dir>; Steam app 1247090 is only a redirect stub"
    ),
]

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    require_proton,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.stormworksserver import steam_app_id
START_TIMEOUT = 600
STOP_TIMEOUT = 90
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "stormworksserver"


def test_stormworksserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "screen", runtime_backend=runtime_backend, module_name=module_name
    )
    require_proton()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itstormworksse"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # Stormworks app 1247090 is now a stub that prints a redirect message
        # ("dedicated server has been moved") and exits; the real server ships
        # with the purchased game.  Detect that message early so the test skips
        # in seconds rather than waiting out the full START_TIMEOUT.
        log_text = wait_for_runtime_log_marker(
            env,
            server_name,
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
