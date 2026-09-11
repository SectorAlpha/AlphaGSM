"""Integration test for codwawserver."""

import os
import sys

import pytest

from conftest import (
    require_integration_opt_in,
    require_command_for_runtime,
    default_runtime_backend,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_codwawserver_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "codwawserver"
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itcodwawserver"
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
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "quake", START_TIMEOUT, expected_port=port)

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding (Quake status on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Server info (Quake status on port" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "quake", (
            f"Expected quake protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected quake info to report the bound port: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected no players on the fresh server: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)

    # verify stopped
    wait_for_generic_udp_closed(
        "127.0.0.1", port, STOP_TIMEOUT, payload=b"\xff\xff\xff\xffgetstatus\n"
    )
