"""Integration test for enshrouded."""

import json
import os

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    log_command_result,
    pick_free_tcp_port,
    require_command_for_runtime,
    resolve_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    run_setup_with_port_retry,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    wait_for_udp_closed,
    write_config,
)

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 1800
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "enshrouded"
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_enshrouded_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itenshro" + tmp_path.name.replace("_", "")[-7:])[:15]
    image = resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
        LOCAL_WINE_PROTON_IMAGE,
        PUBLISHED_WINE_PROTON_IMAGE,
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
    port = pick_free_tcp_port()
    queryport = pick_free_tcp_port()
    while queryport == port:
        queryport = pick_free_tcp_port()

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

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
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

    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
    wait_for_udp_closed("127.0.0.1", queryport, STOP_TIMEOUT)
