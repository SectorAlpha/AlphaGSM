"""Integration test for cod2server."""

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
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_cod2server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itcod2server"
    image = os.environ.get(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX",
        "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest",
    )

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="docker",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "cod2server")
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

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
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "No further details available." in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected tcp info to report the bound port: {_info_data!r}"
        )
        assert "latency_ms" in _info_data, (
            f"Expected tcp info to include latency: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
