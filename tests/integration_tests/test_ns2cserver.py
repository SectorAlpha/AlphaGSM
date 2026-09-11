"""Integration test for ns2cserver."""

import json
import os
import sys

import pytest

from conftest import (
    alphagsm_env,
    capture_alphagsm_stop,
    default_runtime_backend,
    pick_free_tcp_port_group,
    require_command_for_runtime,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)
pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_ns2cserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "ns2cserver"
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itns2cserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-NS2C-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)
    query_port = port + 1

    run_and_assert_ok(
        env,
        server_name,
        "create",
        module_name,
        allow_known_steamcmd_skip=False,
    )

    run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        allow_known_steamcmd_skip=False,
    )

    assert (install_dir / server_name).is_dir()
    assert (install_dir / server_name / "Workshop").is_dir()
    assert (install_dir / "ia32" / "ns2combatserver_linux32").exists()

    run_and_assert_ok(
        env,
        server_name,
        "start",
        allow_known_steamcmd_skip=False,
    )

    try:
        wait_for_info_protocol(
            env,
            server_name,
            "a2s",
            START_TIMEOUT,
            expected_port=query_port,
        )

        run_and_assert_ok(
            env,
            server_name,
            "status",
            allow_known_steamcmd_skip=False,
        )

        query_result = run_and_assert_ok(
            env,
            server_name,
            "query",
            allow_known_steamcmd_skip=False,
        )
        assert "Server is responding" in query_result.stdout

        info_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            allow_known_steamcmd_skip=False,
        )
        assert "Protocol" in info_result.stdout

        info_json_result = run_and_assert_ok(
            env,
            server_name,
            "info",
            "--json",
            allow_known_steamcmd_skip=False,
        )
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", info_data
        assert info_data["port"] == query_port, info_data
    finally:
        stop_result = capture_alphagsm_stop(
            env,
            server_name,
            sys.exc_info()[1],
        )

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
