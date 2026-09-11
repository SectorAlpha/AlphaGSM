"""Integration test for ahl2server."""

import json
import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_tcp_open,
    wait_for_tcp_closed,
)
from gamemodules.ahl2server import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_ahl2server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name="ahl2server",
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itahl2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name="ahl2server",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "ahl2server")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # The current payload does not emit the usual Source readiness markers,
        # but it exposes the module's declared TCP health endpoint once ready.
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        info_data = wait_for_info_protocol(
            env, server_name, "tcp", START_TIMEOUT, expected_port=port
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        assert info_data["protocol"] == "tcp"
        wait_for_tcp_open("127.0.0.1", port, 600, log_path=log_path)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "TCP ping on port" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == port, (
            f"Expected TCP game port {port}: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
