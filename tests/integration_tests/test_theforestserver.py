"""Integration test for theforestserver."""

import json
import os
import sys

import pytest

from conftest import (
    alphagsm_env,
    assert_alphagsm_result_ok,
    capture_alphagsm_stop,
    default_runtime_backend,
    pick_free_tcp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    require_proton,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
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

    dump_result = run_and_assert_ok(env, server_name, "dump")
    query_port = int(json.loads(dump_result.stdout)["queryport"])
    dump_result = None

    try:
        # start
        run_and_assert_ok(env, server_name, "start")

        # The Forest writes its Steam CM log to logs/connection_log_27015.txt
        # (port 27015 is the hardcoded game-server Steam auth port).
        # "[Logged On" appears when Steam auth succeeds and the server is ready.
        server_log = install_dir / "logs" / "connection_log_27015.txt"
        wait_for_log_marker(
            server_log,
            ["[Logged On"],
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        query_ready = "Server is responding" in query_result.stdout
        query_result = None
        assert query_ready, "Expected The Forest query readiness"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        info_ready = "Players     : 0/" in info_result.stdout
        info_result = None
        assert info_ready, "Expected The Forest info readiness"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        info_protocol = _info_data.get("protocol")
        info_players = _info_data.get("players")
        info_port = _info_data.get("port")
        _info_data = None
        info_json_result = None
        assert info_protocol == "a2s", "Expected a2s protocol in info JSON"
        assert info_players == 0, "Expected 0 players on fresh server"
        assert info_port == query_port, "Expected selected queryport in info JSON"
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env,
            server_name,
            sys.exc_info()[1],
        )

    # verify stopped
    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
