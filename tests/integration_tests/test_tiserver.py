"""Integration test for tiserver."""

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
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
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


@pytest.mark.skip(
    reason="ENABLED (AUTH): The Isle dedicated server now installs anonymously on Linux, but start still requires eos_client_id and eos_client_secret for Epic Online Services dedicated-server authentication"
)
@pytest.mark.timeout(TEST_TIMEOUT)
def test_tiserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("ittisle" + tmp_path.name.replace("_", "")[-8:])[:15]
    image = resolve_steamcmd_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="tiserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()
    queryport = pick_free_tcp_port()

    run_and_assert_ok(env, server_name, "create", "tiserver")
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
        info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)
        assert info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("port") == port, (
            f"Expected managed game-port TCP readiness on fresh server: {info_data!r}"
        )

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "TCP ping on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "No further details available." in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        import json as _info_json

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = _info_json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("port") == port, (
            f"Expected managed game-port TCP readiness on fresh server: {info_data!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
