"""Integration test for dysserver."""

import json
import os

import pytest

from conftest import (
    alphagsm_env,
    assert_source_server_empty,
    default_runtime_backend,
    find_source_server_cfg,
    log_command_result,
    pick_free_udp_port,
    require_command_for_runtime,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    run_setup_with_port_retry,
    run_alphagsm,
    skip_for_known_steamcmd_issue,
    set_source_hibernation,
    wait_for_a2s_ready,
    wait_for_info_protocol,
    wait_for_runtime_log_marker,
    wait_for_udp_closed,
    write_config,
    resolve_steamcmd_linux_runtime_image,
)
from gamemodules.dysserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason=(
            "ENABLED (AUTH): authenticate Steam or SteamCMD with an account that can "
            "access Dystopia Beta Dedicated Server app 17595 before setup; anonymous "
            "SteamCMD returns No subscription on the supported Previous/beta path"
        )
    ),
]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 1800
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "dysserver"


@pytest.mark.timeout(SETUP_TIMEOUT + START_TIMEOUT + 600)
def test_dysserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itdysserver"
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
    port = pick_free_udp_port()
    clientport = pick_free_udp_port()
    while clientport == port:
        clientport = pick_free_udp_port()
    sourcetvport = pick_free_udp_port()
    while sourcetvport in {port, clientport}:
        sourcetvport = pick_free_udp_port()
    query_host = detect_query_host()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "clientport", str(clientport))
    run_and_assert_ok(env, server_name, "set", "sourcetvport", str(sourcetvport))

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
    assert result.returncode == 0, result.stderr or result.stdout

    server_cfg_path = find_source_server_cfg(install_dir)
    set_source_hibernation(server_cfg_path, enabled=False)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["SV_ActivateServer", "Connection to Steam servers successful", "VAC secure mode"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        assert_source_server_empty(info_data)

        wait_for_a2s_ready(query_host, port, START_TIMEOUT, log_path=log_path)

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
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, (
            f"Expected A2S query port {port}: {info_data!r}"
        )
        assert_source_server_empty(info_data)
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
