"""Integration test for minecraft.bedrock."""

import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    default_runtime_backend,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)

pytestmark = pytest.mark.integration

SETUP_TIMEOUT = 3600
START_TIMEOUT = 900
STOP_TIMEOUT = 90
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_DOCKER_IMAGE = "alphagsm-service-console-runtime:local"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-service-console-runtime:latest"
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "minecraft.bedrock"


def resolve_service_console_runtime_image():
    """Prefer an explicit or local service-console runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_WRAPPER_DOCKER_IMAGE_SERVICE_CONSOLE")
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


@pytest.mark.timeout(TEST_TIMEOUT)  # Allow the full download budget plus Bedrock startup and shutdown
def test_minecraft_bedrock_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itminecraftbed" + tmp_path.name.replace("_", "")[-8:])[:15]
    image = resolve_service_console_runtime_image()

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
    result = run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        info_data = wait_for_info_protocol(env, server_name, "bedrock", START_TIMEOUT)
        assert info_data["protocol"] == "bedrock", (
            f"Expected Bedrock protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, f"Expected matching Bedrock port in info JSON: {info_data!r}"

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
        assert (
            "Name        :" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "bedrock", (
            f"Expected Bedrock protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == port, (
            f"Expected matching Bedrock port in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players_online") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
