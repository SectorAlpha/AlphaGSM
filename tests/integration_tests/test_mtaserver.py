"""Integration test for mtaserver."""

import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port_group,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    wait_for_udp_closed,
    resolve_steamcmd_linux_runtime_image,
)

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "mtaserver"


def test_mtaserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itmta" + tmp_path.name.replace("_", "")[-10:])[:15]
    image = resolve_steamcmd_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(3)
    httpport = port + 2

    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))

    run_and_assert_ok(env, server_name, "start")

    try:
        info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)
        assert info_data["protocol"] == "tcp", f"Expected tcp protocol in info JSON: {info_data!r}"
        assert info_data["port"] == httpport, f"Expected matching http port in info JSON: {info_data!r}"

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "TCP ping on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "TCP ping on port" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        import json as _info_json

        info_data = _info_json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "tcp", f"Expected tcp protocol in info JSON: {info_data!r}"
        assert info_data["port"] == httpport, (
            f"Expected matching http port in info JSON: {info_data!r}"
        )
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_tcp_closed("127.0.0.1", httpport, STOP_TIMEOUT)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
