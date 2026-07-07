"""Integration test for hcuserver."""

import json
import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_glob_log_marker,
    wait_for_info_protocol,
    wait_for_udp_open,
    wait_for_generic_udp_closed,
)
from gamemodules.hcuserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
READY_MARKERS = ("listening on port",)


def test_hcuserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "hcuserver"
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "ithcuserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_host = detect_query_host()

    run_and_assert_ok(env, server_name, "create", module_name)

    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    run_and_assert_ok(env, server_name, "start")

    try:
        log_dir = install_dir / "Unboxed" / "Saved" / "Logs"
        log_path = log_dir / "Unboxed.log"
        wait_for_glob_log_marker(
            log_dir,
            "Unboxed*.log",
            READY_MARKERS,
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )
        wait_for_udp_open(query_host, port, START_TIMEOUT, log_path=log_path)

        run_and_assert_ok(env, server_name, "status")

        wait_for_info_protocol(env, server_name, "udp", 300)

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
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_generic_udp_closed(query_host, port, STOP_TIMEOUT)
