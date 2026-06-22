"""Integration test for kerbalspaceprogramserver."""

import json
import os
import subprocess

import pytest

from conftest import (
    alphagsm_env,
    log_command_result,
    pick_free_udp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    wait_for_info_protocol,
    wait_for_udp_closed,
    write_config,
)

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"
runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "kerbalspaceprogramserver"


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


def test_kerbalspaceprogramserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itksp" + tmp_path.name.replace("_", "")[-10:])[:15]
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

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        info_data = wait_for_info_protocol(env, server_name, "udp", START_TIMEOUT)
        assert info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("port") == port, (
            f"Expected managed UDP port in info JSON: {info_data!r}"
        )
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
        info_json = json.loads(info_json_result.stdout.strip())
        assert info_json["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_json!r}"
        )
        assert info_json.get("port") == port, (
            f"Expected managed UDP port in info JSON: {info_json!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
