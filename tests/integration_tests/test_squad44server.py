"""squad44server Workshop plugin mounting through real process and Docker lifecycles."""

import json
import os
from pathlib import Path
import re
import sys

import pytest

from conftest import (
    alphagsm_env, assert_alphagsm_result_ok, capture_alphagsm_stop,
    default_runtime_backend, effective_runtime_backend, require_command,
    pick_free_tcp_port_group, require_command_for_runtime, require_integration_opt_in,
    require_steamcmd_opt_in, resolve_steamcmd_linux_runtime_image, run_and_assert_ok,
    run_setup_with_port_retry, wait_for_glob_log_marker, wait_for_info_protocol,
    wait_for_udp_closed, wait_for_runtime_log_marker, write_config,
    workshop_runtime_backends,
)
from server.modsupport.workshop import normalize_workshop_identifier
from tests.integration_tests.squad44_sdk_diagnostics import sdk_metadata_from_config
from tests.smoke_tests.squad44server_workshop import (
    FIXTURE_ID, staged_plugin_name, select_workshop_layer, configure_workshop_layer,
    wait_for_native_map, assert_workshop_map_info,
)

pytestmark = pytest.mark.integration
START_TIMEOUT = 900
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600


@pytest.mark.timeout(SETUP_TIMEOUT + START_TIMEOUT + 600)
def test_squad44server_lifecycle(tmp_path, *, runtime_backend=None, workshop=None):
    """Require a stock native world, real A2S health and complete shutdown."""
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "squad44server"
    effective_backend = effective_runtime_backend(runtime_backend, module_name=module_name)
    if effective_backend == "docker":
        require_command("docker")
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
    if effective_backend == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    result, port = run_setup_with_port_retry(
        env, server_name, port, install_dir, timeout=SETUP_TIMEOUT)
    assert_alphagsm_result_ok(result)
    print("[native-sdk]", json.dumps(sdk_metadata_from_config(install_dir, config_path),
                                     sort_keys=True))
    if workshop:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", workshop[0])
        run_and_assert_ok(env, server_name, "mod", "apply")
        workshop = (workshop[0], staged_plugin_name(install_dir, workshop[0], workshop[1]))
        layer = select_workshop_layer(workshop[0], os.environ.get("ALPHAGSM_SQUAD44_WORKSHOP_LAYER", ""))
        configure_workshop_layer(install_dir, layer)
    log_dir = install_dir / "PostScriptum/Saved/Logs"
    if log_dir.exists():
        for path in log_dir.glob("*.log"):
            path.rename(path.with_suffix(".previous"))
    try:
        run_and_assert_ok(env, server_name, "start")
        wait_for_runtime_log_marker(env, server_name, ["LogPakFile", "LogPluginManager"],
                                    START_TIMEOUT)
        native_log = wait_for_glob_log_marker(
            log_dir, "*.log", ["LogLoad: (Engine Initialization)"], START_TIMEOUT,
            env=env, server_name=server_name)
        if workshop:
            native_log = wait_for_native_map(log_dir, layer, START_TIMEOUT)
        else:
            assert re.search(r"LogLoad: Took .*LoadMap\(/Game/", native_log), native_log[-8000:]
        # Preserve initialization evidence that falls outside the usual timeout tail.
        for line in native_log.splitlines():
            if any(marker in line for marker in ("LogOnline:", "STEAM:", "SteamGameServer",
                                                  "LogRCONServer:", "SteamNetDriver", "LogEOS:")):
                print("[native-startup]", line)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=port + 1)
        if workshop:
            plugin = re.escape(workshop[1])
            native_log = wait_for_glob_log_marker(
                log_dir, "*.log", [workshop[1]], START_TIMEOUT, env=env, server_name=server_name)
            assert re.search(r"LogPakFile:.*Mounted Pak file.*" + plugin + r".*\.pak", native_log), native_log[-8000:]
            assert re.search(r"LogModdingRuntimeModule:.*(?:[Mm]ounted|[Ss]eriali[sz]ed).*" + plugin,
                             native_log), native_log[-8000:]
        run_and_assert_ok(env, server_name, "status")
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players     : 0/" in info_result.stdout
        info_json = run_and_assert_ok(env, server_name, "info", "--json")
        info = json.loads(info_json.stdout.strip())
        assert info["protocol"] == "a2s" and info["port"] == port + 1
        if workshop:
            assert_workshop_map_info(info, layer)
    finally:
        stop = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT)
        if workshop and stop is not None and stop.returncode == 0:
            run_and_assert_ok(env, server_name, "mod", "cleanup")
    assert_alphagsm_result_ok(stop)
    wait_for_udp_closed("127.0.0.1", port + 1, STOP_TIMEOUT)
    if workshop:
        assert not list((install_dir / "PostScriptum/Plugins/Mods" / workshop[0]).rglob("*.pak"))


@pytest.mark.timeout(SETUP_TIMEOUT + START_TIMEOUT + 600)
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_squad44server_native_workshop(tmp_path, runtime_backend):
    """Require anonymous Linux content, native plugin loading and actual A2S health."""
    if (os.environ.get("ALPHAGSM_RUN_SQUAD44_WORKSHOP") != "1"
            and os.environ.get("ALPHAGSM_CI_WORKSHOP") != "1"):
        pytest.skip("Set ALPHAGSM_RUN_SQUAD44_WORKSHOP=1 for native public Workshop checks")
    item = os.environ.get("ALPHAGSM_SQUAD44_WORKSHOP_ID", FIXTURE_ID)
    plugin = os.environ.get("ALPHAGSM_SQUAD44_WORKSHOP_PLUGIN", "")
    assert item and (not plugin or re.fullmatch(r"[A-Za-z0-9_-]+", plugin)), (
        "Set a public Linux fixture ID/URL and optional exact staged plugin name")
    item = normalize_workshop_identifier(item)
    assert item != "2909251852", "SquidBots has obsolete Engine=4.27.2; the current SDK uses 4.27.2.SQ44"
    test_squad44server_lifecycle(tmp_path, runtime_backend=runtime_backend, workshop=(item, plugin))
