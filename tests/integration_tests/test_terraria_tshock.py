"""Integration test for terraria.tshock."""

import os

import pytest

from conftest import (
    alphagsm_env,
    log_command_result,
    pick_free_tcp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    run_and_assert_ok,
    run_alphagsm,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    write_config,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "terraria.tshock"


def test_terraria_tshock_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itterrariatsho"
    image = os.environ.get(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX",
        "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest",
    )

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

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
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
        assert (
            "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        run_and_assert_ok(env, server_name, "info")

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", f"Expected tcp protocol in info JSON: {_info_data!r}"
        assert _info_data["port"] == port, f"Expected matching TCP port in info JSON: {_info_data!r}"
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
