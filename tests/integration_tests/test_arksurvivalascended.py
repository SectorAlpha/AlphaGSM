"""Integration test for arksurvivalascended."""

import json
import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    resolve_runtime_image,
    pick_free_tcp_port,
    pick_free_udp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
    wait_for_tcp_closed,
)

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 1800
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: very large SteamCMD payload under shared CI load
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


@pytest.mark.timeout(TEST_TIMEOUT)  # Allow the full download budget plus slow first-launch init
def test_arksurvivalascended_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itasa" + tmp_path.name.replace("_", "")[-10:])[:15]
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
        runtime_backend="docker",
        module_name="arksurvivalascended",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    rconport = pick_free_tcp_port()
    while rconport == port:
        rconport = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "arksurvivalascended")
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "rconport", str(rconport))

    # setup
    _setup_result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    dump_result = run_and_assert_ok(env, server_name, "dump")
    rconport = int(json.loads(dump_result.stdout)["rconport"])

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        info_data = wait_for_info_protocol(
            env,
            server_name,
            "source_rcon",
            START_TIMEOUT,
            expected_port=rconport,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert f"Server is responding (Source RCON on port {rconport})" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert f"Server info (Source RCON on port {rconport}):" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_json = json.loads(info_json_result.stdout.strip())
        assert info_json["protocol"] == "source_rcon", (
            f"Expected source_rcon protocol in info JSON: {info_json!r}"
        )
        assert info_json["port"] == rconport, (
            f"Expected RCON port {rconport} in info JSON: {info_json!r}"
        )
        assert info_data["protocol"] == info_json["protocol"]
        assert info_data["port"] == info_json["port"]
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    # verify stopped
    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    wait_for_tcp_closed("127.0.0.1", rconport, STOP_TIMEOUT)
    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
