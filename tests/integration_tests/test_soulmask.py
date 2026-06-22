"""Integration test for soulmask."""

import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_udp_closed,
)
from gamemodules.soulmask import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "soulmask"
LOCAL_DOCKER_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


def resolve_wine_proton_runtime_image():
    """Prefer a branch-local Wine/Proton runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON")
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
def test_soulmask_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itsoul" + tmp_path.name.replace("_", "")[-9:])[:15]
    image = resolve_wine_proton_runtime_image()

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
    echoport = pick_free_tcp_port()

    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))
    run_and_assert_ok(env, server_name, "set", "echoport", str(echoport))

    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    run_and_assert_ok(env, server_name, "start")

    try:
        _info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected Soulmask tcp readiness on the managed game port: {_info_data!r}"
        )

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "TCP ping on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "TCP ping on port" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected Soulmask tcp readiness on the managed game port: {_info_data!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_udp_closed("127.0.0.1", queryport, STOP_TIMEOUT)
