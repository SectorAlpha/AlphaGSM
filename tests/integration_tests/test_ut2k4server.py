"""Integration test for ut2k4server."""

import json
import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_log_marker,
    wait_for_udp_closed,
    wait_for_udp_open,
)

pytestmark = pytest.mark.integration

SETUP_TIMEOUT = 3600
START_TIMEOUT = 600
STOP_TIMEOUT = 90
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
READY_MARKERS = (
    "Bringing Level",
    "UdpServerQuery",
)


@pytest.mark.timeout(TEST_TIMEOUT)
def test_ut2k4server_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name="ut2k4server",
    )
    require_command("7z")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itut2k4server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name="ut2k4server",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "ut2k4server")

    # setup
    run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=SETUP_TIMEOUT,
    )

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            READY_MARKERS,
            START_TIMEOUT,
        )
        wait_for_udp_open("127.0.0.1", port, START_TIMEOUT, log_path=log_path)

        # status
        status_result = run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_result.stdout

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Server port is open" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"
        assert "No further details available." in info_result.stdout, (
            f"Expected generic UDP info output: {info_result.stdout!r}"
        )

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, f"Expected matching UDP port in info JSON: {info_data!r}"
        assert "latency_ms" in info_data, (
            f"Expected latency in UDP info JSON: {info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
