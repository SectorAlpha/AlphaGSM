"""Integration test for ut99server."""

import json

import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_alphagsm,
    run_and_assert_ok,
    log_command_result,
    wait_for_log_marker,
    wait_for_udp_open,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
READY_MARKERS = (
    "Init: Unreal engine initialized",
    "UdpServerQuery",
)


def test_ut99server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("screen")
    require_command("7z")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itut99server"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()

    run_and_assert_ok(env, server_name, "create", "ut99server")

    setup_result = run_alphagsm(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
    )
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        setup_result,
    )
    assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(log_path, READY_MARKERS, START_TIMEOUT)
        wait_for_udp_open("127.0.0.1", port, START_TIMEOUT, log_path=log_path)

        status_result = run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_result.stdout

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "UDP ping on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "UDP ping on port" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )
        assert "No further details available." in info_result.stdout, (
            f"Expected generic UDP info output: {info_result.stdout!r}"
        )

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, (
            f"Expected reported info port {port}: {info_data!r}"
        )
        assert "latency_ms" in info_data, (
            f"Expected latency in UDP info JSON: {info_data!r}"
        )
    finally:
        log_command_result(
            "alphagsm stop",
            run_alphagsm(env, server_name, "stop"),
        )

    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
