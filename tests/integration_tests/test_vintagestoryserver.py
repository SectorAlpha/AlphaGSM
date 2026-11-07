"""Integration test for vintagestoryserver."""

import os

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
    wait_for_tcp_closed,
    resolve_steamcmd_linux_runtime_image,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"


def test_vintagestoryserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itvintagestory"
    image = resolve_steamcmd_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="vintagestoryserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "vintagestoryserver")
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server port is open" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Server port is open" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        _info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)
        assert _info_data["protocol"] == "tcp", f"Expected tcp protocol in info JSON: {_info_data!r}"
        assert _info_data["port"] == port, f"Expected matching TCP port in info JSON: {_info_data!r}"
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
