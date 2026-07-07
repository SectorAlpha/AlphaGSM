"""Integration test for theforestserver."""

import os

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    log_command_result,
    pick_free_tcp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    require_proton,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
    write_config,
)
from gamemodules.theforestserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_theforestserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_proton()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "theforestserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "ittheforestser"

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
        # The Forest writes its Steam CM log to logs/connection_log_27015.txt
        # (port 27015 is the hardcoded game-server Steam auth port).
        # "[Logged On" appears when Steam auth succeeds and the server is ready.
        server_log = install_dir / "logs" / "connection_log_27015.txt"
        wait_for_log_marker(
            server_log,
            ["[Logged On"],
            START_TIMEOUT,
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
