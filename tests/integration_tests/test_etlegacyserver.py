"""Integration test for etlegacyserver."""

import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    wait_for_udp_closed,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): requires original Wolfenstein: Enemy Territory base assets (etmain/pak0.pk3) not available in CI"
    ),
]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
LOCAL_DOCKER_IMAGE = "alphagsm-quake-linux-runtime:local"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:latest"


def resolve_quake_linux_runtime_image():
    """Prefer a branch-local Quake runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_QUAKE_LINUX")
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


def test_etlegacyserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itetlegacyserv"
    image = resolve_quake_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="etlegacyserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "etlegacyserver")
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        _info_data = wait_for_info_protocol(env, server_name, "quake", START_TIMEOUT)
        assert _info_data["protocol"] == "quake", (
            f"Expected quake protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected ET: Legacy quake readiness on the managed game port: {_info_data!r}"
        )

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
            "Players : 0/" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "quake", (
            f"Expected quake protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
