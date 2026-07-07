"""Integration test for palworld."""

import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    default_runtime_backend,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    run_setup_with_port_retry,
    wait_for_a2s_ready,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
    resolve_steamcmd_linux_runtime_image,
)
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 900
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_STEAMCMD_LINUX_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_STEAMCMD_LINUX_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "palworld"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_palworld_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itpalworld" + tmp_path.name.replace("_", "")[-5:])[:15]
    image = resolve_steamcmd_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    queryport = pick_free_udp_port()
    while queryport == port:
        queryport = pick_free_udp_port()
    query_host = detect_query_host()

    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))

    _setup_result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )

    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_a2s_ready(query_host, queryport, START_TIMEOUT)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players     : 0/" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        import json as _info_json

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = _info_json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {info_data!r}"
        )
        assert info_data.get("port") == queryport, (
            f"Expected query port {queryport} in info JSON: {info_data!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_generic_udp_closed(query_host, queryport, STOP_TIMEOUT)
