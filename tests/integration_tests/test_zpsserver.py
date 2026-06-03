"""Integration test for zpsserver."""

import json
import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_setup_with_port_retry,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_a2s_ready,
    wait_for_udp_closed,
)
from gamemodules.zpsserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason=(
            "ENABLED (AUTH): install and run an authenticated Steam client session "
            "alongside Zombie Panic! Dedicated Server app 4523420 before start; "
            "even with the SteamDB-advertised -steam -secure launch flags, HLDS "
            "still reports SteamAPI_IsSteamRunning() missing under the anonymous "
            "Docker lane"
        )
    ),
]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 1200
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"


def resolve_steamcmd_linux_runtime_image():
    """Prefer an explicit or local SteamCMD Linux runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX")
    if configured_image:
        return configured_image

    local_image = subprocess.run(
        ["docker", "image", "inspect", LOCAL_DOCKER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if local_image.returncode == 0:
        return LOCAL_DOCKER_IMAGE

    return PUBLISHED_DOCKER_IMAGE


@pytest.mark.timeout(TEST_TIMEOUT)
def test_zpsserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itzps" + tmp_path.name.replace("_", "")[-10:])[:15]
    image = resolve_steamcmd_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="zpsserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    clientport = pick_free_udp_port()
    while clientport == port:
        clientport = pick_free_udp_port()
    query_host = detect_query_host()

    # create
    run_and_assert_ok(env, server_name, "create", "zpsserver")
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "clientport", str(clientport))

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

    run_and_assert_ok(env, server_name, "set", "servername", "AlphaGSM ZPS IT")

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_a2s_ready(query_host, port, START_TIMEOUT)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players     : 0/" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["map"] == "zph_industry", (
            f"Expected zph_industry map in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
