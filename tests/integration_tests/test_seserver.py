"""Integration test for seserver."""

import json
import os
import subprocess

import pytest

from conftest import (
    require_command,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    pick_free_udp_port,
    run_alphagsm,
    run_and_assert_ok,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    log_command_result,
    wait_for_generic_udp_closed,
    wait_for_info_protocol,
)
from gamemodules.seserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


def resolve_wine_proton_runtime_image():
    """Prefer a branch-local Wine/Proton runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON")
    if configured_image:
        return configured_image

    local_image = subprocess.run(
        ["docker", "image", "inspect", LOCAL_WINE_PROTON_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if local_image.returncode == 0:
        return LOCAL_WINE_PROTON_IMAGE

    return PUBLISHED_WINE_PROTON_IMAGE


@pytest.mark.timeout(TEST_TIMEOUT)
def test_seserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itse" + tmp_path.name.replace("_", "")[-11:])[:15]
    image = resolve_wine_proton_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="seserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()

    run_and_assert_ok(env, server_name, "create", "seserver")
    run_and_assert_ok(env, server_name, "set", "image", image)

    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Space Engineers setup failed unexpectedly for app {steam_app_id}: "
            f"{result.stdout}\n{result.stderr}"
        )

    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "udp", START_TIMEOUT)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "UDP ping on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "No further details available." in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("port") == port, (
            f"Expected game port in info JSON: {info_data!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
