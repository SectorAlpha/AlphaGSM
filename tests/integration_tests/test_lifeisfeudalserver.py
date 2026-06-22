"""
Integration test for lifeisfeudalserver.

AlphaGSM can launch a managed Docker MariaDB sidecar for Life is Feudal, so
the lifecycle can run end to end without a separately installed local MySQL
service.
"""

from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = [pytest.mark.integration]

from conftest import (
    alphagsm_env,
    log_command_result,
    pick_free_tcp_port,
    require_command,
    require_command_for_runtime,
    require_integration_opt_in,
    require_proton,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    run_setup_with_port_retry,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_closed,
    write_config,
)
from gamemodules.lifeisfeudalserver import _managed_db_container_name, steam_app_id

SETUP_TIMEOUT = 3600
START_TIMEOUT = 600
STOP_TIMEOUT = 120
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


def _docker_rm_force(name):
    subprocess.run(
        ["docker", "rm", "-f", name],
        check=False,
        capture_output=True,
        text=True,
    )


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


def test_lifeisfeudalserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    module_name = "lifeisfeudalserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    require_command("docker")
    image = None
    if runtime_backend == "process":
        require_proton()
    else:
        image = resolve_wine_proton_runtime_image()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = f"lifdb{tmp_path.name[-6:]}"
    db_container_name = _managed_db_container_name(type("ServerRef", (), {"name": server_name})())

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()
    db_port = pick_free_tcp_port()

    _docker_rm_force(db_container_name)

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
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    for key, value in (
        ("db_mode", "docker"),
        ("db_host", "127.0.0.1"),
        ("db_port", str(db_port)),
        ("db_name", "lif_1"),
        ("db_user", "root"),
        ("db_password", "alphagsm-lif-secret"),
    ):
        run_and_assert_ok(env, server_name, "set", key, value)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout, query_result.stdout

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players" in info_result.stdout, info_result.stdout

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        assert '"protocol":' in info_json_result.stdout, info_json_result.stdout
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))
        _docker_rm_force(db_container_name)

    wait_for_tcp_closed("127.0.0.1", db_port, STOP_TIMEOUT)
