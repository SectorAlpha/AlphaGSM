"""Integration test for astroneerserver."""

import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    resolve_runtime_image,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    run_setup_with_port_retry,
    wait_for_glob_log_marker,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)
from gamemodules.astroneerserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: large SteamCMD payload under shared CI load
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_astroneerserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itastr" + tmp_path.name.replace("_", "")[-9:])[:15]
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
        runtime_backend="auto",
        module_name="astroneerserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "astroneerserver")
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "dir", str(install_dir))

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_glob_log_marker(
            install_dir / "Astro" / "Saved" / "Logs",
            "*.log",
            (f"IpNetDriver listening on port {port}",),
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )
        info_data = wait_for_info_protocol(
            env,
            server_name,
            "udp",
            START_TIMEOUT,
            expected_port=port,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert f"Server port is open (UDP ping on port {port} -" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert f"Server port is open (UDP ping on port {port} -" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_json = _info_json.loads(info_json_result.stdout.strip())
        assert info_json["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_json!r}"
        )
        assert info_json["port"] == port, (
            f"Expected info port {port} in info JSON: {info_json!r}"
        )
        assert info_data["protocol"] == info_json["protocol"]
        assert info_data["port"] == info_json["port"]
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    # verify stopped
    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
