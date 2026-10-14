"""ARK native mod descriptor and asset loading through AlphaGSM."""

import json
import os
from pathlib import Path
import re
import sys
import time

import pytest
from ark_workshop_helpers import wait_for_loaded_world

from conftest import (
    workshop_runtime_backends,
    alphagsm_env, assert_alphagsm_result_ok, capture_alphagsm_stop,
    default_runtime_backend, effective_runtime_backend, require_command,
    pick_free_tcp_port_group, pick_free_udp_port, require_integration_opt_in,
    require_steamcmd_opt_in, resolve_steamcmd_linux_runtime_image, run_and_assert_ok,
    run_setup_with_port_retry, wait_for_glob_log_marker, wait_for_info_protocol,
    wait_for_udp_closed, write_config,
)

pytestmark = pytest.mark.integration
SETUP_TIMEOUT = 3600
START_TIMEOUT = 1800
STOP_TIMEOUT = 90


@pytest.mark.timeout(SETUP_TIMEOUT + START_TIMEOUT + 600)
def test_ark_lifecycle(tmp_path):
    """Run the stock baseline once using the selected CI runtime."""
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    _run_ark_lifecycle(tmp_path, runtime_backend=runtime_backend)


def _run_ark_lifecycle(tmp_path, *, runtime_backend, workshop=False):
    """Require a native loaded world, real A2S health and full shutdown."""
    require_integration_opt_in()
    require_steamcmd_opt_in()
    effective_backend = effective_runtime_backend(runtime_backend, module_name="ark")
    if effective_backend == "docker":
        require_command("docker")
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = Path(os.environ.get("ALPHAGSM_ARK_INSTALL_DIR", tmp_path / "server"))
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itark" + tmp_path.name[-7:])[:15]
    write_config(config_path, home_dir, backend="subprocess", runtime_backend=runtime_backend,
                 module_name="ark")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)
    query_port = pick_free_udp_port()
    while query_port in (port, port + 1):
        query_port = pick_free_udp_port()
    run_and_assert_ok(env, server_name, "create", "ark")
    if effective_backend == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    run_and_assert_ok(env, server_name, "set", "queryport", str(query_port))
    result, port = run_setup_with_port_retry(
        env, server_name, port, install_dir, timeout=SETUP_TIMEOUT)
    assert_alphagsm_result_ok(result)
    if workshop:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop",
                          "https://steamcommunity.com/sharedfiles/filedetails/?id=2860800256")
        run_and_assert_ok(env, server_name, "mod", "apply")
        engine = install_dir / "ShooterGame/Saved/Config/LinuxServer/Engine.ini"
        with engine.open("a", encoding="utf-8") as handle:
            handle.write("\n[Core.Log]\nLogLinker=Verbose\nLogStreaming=Verbose\nLogUObjectGlobals=Verbose\n")
    log_dir = install_dir / "ShooterGame/Saved/Logs"
    if log_dir.exists():
        for path in log_dir.glob("*.log"):
            path.rename(path.with_suffix(".previous"))
    try:
        run_and_assert_ok(env, server_name, "start")
        readiness_started = time.monotonic()
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=query_port)
        wait_for_loaded_world(
            lambda remaining: wait_for_info_protocol(
                env, server_name, "a2s", remaining, expected_port=query_port),
            START_TIMEOUT - (time.monotonic() - readiness_started))
        if workshop:
            run_and_assert_ok(env, server_name, "send", "getall PrimalGameData_BP_Spoilers_C")
            native_log = wait_for_glob_log_marker(
                log_dir, "*.log", ["PrimalGameData_BP_Spoilers"], START_TIMEOUT,
                env=env, server_name=server_name)
            assert re.search(
                r"Log(?:Linker|Streaming|UObjectGlobals|ConsoleResponse):.*"
                r"(?:Loaded|Created|Loading|Serialize|Linker|PrimalGameData_BP_Spoilers_C).*"
                r"PrimalGameData_BP_Spoilers", native_log), native_log[-8000:]
            assert not re.search(r"(?:Failed|Can't find|Unable).*PrimalGameData_BP_Spoilers",
                                 native_log), native_log[-8000:]
        run_and_assert_ok(env, server_name, "status")
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players     : 0/" in info_result.stdout
        info_json = run_and_assert_ok(env, server_name, "info", "--json")
        info = json.loads(info_json.stdout.strip())
        assert info["protocol"] == "a2s" and info["port"] == query_port
    finally:
        stop = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT)
        if workshop and stop is not None and stop.returncode == 0:
            run_and_assert_ok(env, server_name, "mod", "cleanup")
    assert_alphagsm_result_ok(stop)
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
    if workshop:
        assert not (install_dir / "ShooterGame/Content/Mods/2860800256.mod").exists()


@pytest.mark.timeout(SETUP_TIMEOUT + 2 * START_TIMEOUT + 600)
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_ark_native_workshop(tmp_path, runtime_backend):
    """Keep the unverified native Blueprint fixture separate from baseline health."""
    if os.environ.get("ALPHAGSM_RUN_ARK_WORKSHOP") != "1":
        pytest.skip("Native ARK Workshop object-load proof pending; opt in with ALPHAGSM_RUN_ARK_WORKSHOP=1")
    _run_ark_lifecycle(tmp_path, runtime_backend=runtime_backend, workshop=True)
