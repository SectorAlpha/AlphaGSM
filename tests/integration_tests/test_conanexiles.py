"""Integration test for conanexiles."""

import json
import os
import sys

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    pick_free_tcp_port_group,
    pick_free_udp_port,
    require_command_for_runtime,
    resolve_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    run_and_assert_ok,
    run_setup_with_port_retry,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)
from gamemodules.conanexiles import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 900
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
module_name = "conanexiles"
LOCAL_STEAMCMD_LINUX_IMAGE = "alphagsm-steamcmd-linux-runtime:local"
PUBLISHED_STEAMCMD_LINUX_IMAGE = (
    "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"
)


@pytest.mark.timeout(TEST_TIMEOUT)
def test_conanexiles_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itconan" + tmp_path.name.replace("_", "")[-8:])[:15]
    image = resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX",
        LOCAL_STEAMCMD_LINUX_IMAGE,
        PUBLISHED_STEAMCMD_LINUX_IMAGE,
    )

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)
    queryport = pick_free_udp_port()
    while queryport in (port, port + 1):
        queryport = pick_free_udp_port()

    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))
    run_and_assert_ok(env, server_name, "set", "servername", "AlphaGSM Conan IT")
    run_and_assert_ok(env, server_name, "set", "maxplayers", "16")

    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Conan Exiles setup failed unexpectedly for app {steam_app_id}: "
            f"{result.stdout}\n{result.stderr}"
        )

    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=queryport)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "A2S on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Server info (A2S on port" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )
        assert "Name        : AlphaGSM Conan IT" in info_result.stdout, (
            f"Expected Conan A2S info output: {info_result.stdout!r}"
        )
        assert "Players     : 0/16" in info_result.stdout, (
            f"Expected Conan player counts in info output: {info_result.stdout!r}"
        )

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == queryport, (
            f"Expected reported info port {queryport}: {info_data!r}"
        )
        assert info_data.get("name") == "AlphaGSM Conan IT", (
            f"Expected managed Conan server name in A2S data: {info_data!r}"
        )
    finally:
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", queryport, STOP_TIMEOUT)
