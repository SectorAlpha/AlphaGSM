"""Integration test for primalcarnageextinctionserver."""

import os
import subprocess

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    require_command_for_runtime,
    require_proton,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.primalcarnageextinctionserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
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


def test_primalcarnageextinctionserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    module_name = "primalcarnageextinctionserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    image = None
    if runtime_backend == "process":
        require_proton()
    else:
        require_command("docker")
        image = resolve_wine_proton_runtime_image()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itpce" + tmp_path.name.replace("_", "")[-10:])[:15]

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    if image is not None:
        run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # UE3 dedicated server logs go to PrimalCarnageGame/Logs/Launch.log,
        # not to stdout. The current Primal Carnage build no longer prints the
        # older generic UE3 "Engine is initialized"/"listening on port"
        # markers before A2S is ready, so we wait for its current map bring-up
        # lines and then require a successful info/query round-trip.
        log_path = install_dir / "PrimalCarnageGame" / "Logs" / "Launch.log"
        wait_for_log_marker(
            log_path,
            [
                "LoadMap: PC-Docks",
                "Game class is 'PCTeamDeathMatchGame'",
                "NetMode is now 1",
            ],
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )
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
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
