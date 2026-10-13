"""Authenticated DST lifecycle with optional native Workshop execution evidence."""

import json
import os
from pathlib import Path
import sys

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    effective_runtime_backend,
    require_command_for_runtime,
    pick_free_tcp_port_group,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    wait_for_log_marker,
    wait_for_udp_closed,
    wait_for_info_protocol,
    resolve_steamcmd_linux_runtime_image,
)
from tests.smoke_tests.dst_workshop import (
    WORKSHOP_ITEM_URL, stage_cluster, wait_for_workshop_loaded,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SELECTED_RUNTIME_BACKEND = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
RUNTIME_BACKENDS = [SELECTED_RUNTIME_BACKEND] if "ALPHAGSM_TEST_RUNTIME_BACKEND" in os.environ else [
    "process", "docker",
]


@pytest.mark.parametrize("runtime_backend", RUNTIME_BACKENDS)
def test_dstserver_lifecycle(tmp_path, runtime_backend):
    """Run a fresh disposable Master shard without copying the operator's world."""
    require_integration_opt_in()
    require_steamcmd_opt_in()
    cluster_source = os.environ.get("ALPHAGSM_DST_CLUSTER_SOURCE")
    if not cluster_source:
        pytest.skip("DST requires ALPHAGSM_DST_CLUSTER_SOURCE with a valid Klei cluster token/config")
    cluster_source = Path(cluster_source).expanduser().resolve(strict=True)
    workshop = os.environ.get("ALPHAGSM_RUN_WORKSHOP") == "1"
    require_command_for_runtime("screen", runtime_backend=runtime_backend, module_name="dstserver")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itdstserver"
    write_config(config_path, home_dir, session_tag="AlphaGSM-DST-IT#",
                 runtime_backend=runtime_backend, module_name="dstserver")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(3)
    query_port, auth_port = port + 1, port + 2

    run_and_assert_ok(env, server_name, "create", "dstserver")
    if effective_runtime_backend(runtime_backend, module_name="dstserver") == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    run_and_assert_ok(env, server_name, "set", "queryport", str(query_port))
    run_and_assert_ok(env, server_name, "set", "authport", str(auth_port))
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    cluster = install_dir / "DoNotStarveTogether" / server_name
    stage_cluster(cluster_source, cluster, port, query_port, auth_port)
    log_path = cluster / "Master" / "server_log.txt"
    assert not log_path.exists(), "The readiness and mod evidence must come from this fresh launch"
    if workshop:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", WORKSHOP_ITEM_URL)
        run_and_assert_ok(env, server_name, "mod", "apply")

    run_and_assert_ok(env, server_name, "start")
    try:
        if workshop:
            wait_for_workshop_loaded(log_path, START_TIMEOUT)
        wait_for_log_marker(log_path, ["Online Server Started on port"], START_TIMEOUT)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=query_port)
        run_and_assert_ok(env, server_name, "status")
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players     : 0/" in info_result.stdout
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info = json.loads(info_json_result.stdout.strip())
        assert info["protocol"] == "a2s"
        assert info["port"] == query_port
        assert info["players"] == 0
        assert info["max_players"] > 0
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1],
                                           timeout=STOP_TIMEOUT)
    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
    if workshop:
        run_and_assert_ok(env, server_name, "mod", "cleanup")
        assert not (cluster / "Master" / "modoverrides.lua").exists()
