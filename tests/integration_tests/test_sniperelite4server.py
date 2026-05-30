"""Integration test for sniperelite4server."""

import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    wait_for_tcp_closed,
)

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: large SteamCMD payload under shared CI load
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
def test_sniperelite4server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itse4" + tmp_path.name.replace("_", "")[-10:])[:15]
    image = resolve_wine_proton_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="sniperelite4server",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "sniperelite4server")
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    _setup_result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        _info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected managed game-port TCP readiness on fresh server: {_info_data!r}"
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "TCP ping on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "No further details available." in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected managed game-port TCP readiness on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
