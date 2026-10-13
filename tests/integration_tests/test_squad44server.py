"""squad44server Workshop plugin mounting through real process and Docker lifecycles."""

import json
import os
from pathlib import Path
import re
import sys

import pytest

from conftest import (
    alphagsm_env, assert_alphagsm_result_ok, capture_alphagsm_stop,
    default_runtime_backend,
    pick_free_tcp_port_group, require_command_for_runtime, require_integration_opt_in,
    require_steamcmd_opt_in, resolve_steamcmd_linux_runtime_image, run_and_assert_ok,
    run_setup_with_port_retry, wait_for_glob_log_marker, wait_for_info_protocol,
    wait_for_udp_closed, wait_for_runtime_log_marker, write_config,
)

pytestmark = pytest.mark.integration
START_TIMEOUT = 900
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600


@pytest.mark.timeout(SETUP_TIMEOUT + START_TIMEOUT + 600)
@pytest.mark.parametrize("runtime_backend", ["process", "docker"])
def test_squad44server_lifecycle(tmp_path, runtime_backend):
    """Require exact native mod mounts plus real A2S health and complete shutdown."""
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND",
                                     runtime_backend or default_runtime_backend())
    module_name = "squad44server"
    require_command_for_runtime("screen", runtime_backend=runtime_backend, module_name=module_name)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = Path(os.environ.get("ALPHAGSM_SQUAD44_INSTALL_DIR", tmp_path / "server"))
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itsquad44server" + tmp_path.name[-5:])[:15]
    write_config(config_path, home_dir, backend="subprocess",
                 runtime_backend=runtime_backend, module_name=module_name)
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    result, port = run_setup_with_port_retry(
        env, server_name, port, install_dir, timeout=SETUP_TIMEOUT)
    assert_alphagsm_result_ok(result)
    run_and_assert_ok(env, server_name, "mod", "add", "workshop",
                      "https://steamcommunity.com/sharedfiles/filedetails/?id=2909251852")
    run_and_assert_ok(env, server_name, "mod", "apply")
    log_dir = install_dir / "PostScriptum/Saved/Logs"
    if log_dir.exists():
        for path in log_dir.glob("*.log"):
            path.rename(path.with_suffix(".previous"))
    run_and_assert_ok(env, server_name, "start")
    try:
        wait_for_runtime_log_marker(env, server_name, ["LogPakFile", "LogPluginManager"],
                                    START_TIMEOUT)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=port + 1)
        native_log = wait_for_glob_log_marker(
            log_dir, "*.log", ["SquidBots"], START_TIMEOUT, env=env, server_name=server_name)
        assert re.search(r"LogPakFile:.*Mounted Pak file.*SquidBots.*\.pak", native_log), native_log[-8000:]
        run_and_assert_ok(env, server_name, "status")
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players     : 0/" in info_result.stdout
        info_json = run_and_assert_ok(env, server_name, "info", "--json")
        info = json.loads(info_json.stdout.strip())
        assert info["protocol"] == "a2s" and info["port"] == port + 1
    finally:
        stop = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT)
        if stop is not None and stop.returncode == 0:
            run_and_assert_ok(env, server_name, "mod", "cleanup")
    assert_alphagsm_result_ok(stop)
    wait_for_udp_closed("127.0.0.1", port + 1, STOP_TIMEOUT)
    assert not list((install_dir / "PostScriptum/Plugins/Mods/2909251852").rglob("*.pak"))
