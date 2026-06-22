"""Integration test for wetserver.

Disabled: Wolf: ET ships only a 32-bit dedicated binary, which requires
compatibility libraries not present in CI.
"""

import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    wait_for_log_marker,
    wait_for_quake_ready,
    wait_for_tcp_closed,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Requires 32-bit compat libraries for the original Wolf: ET dedicated server"),
]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_wetserver_lifecycle(tmp_path):
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
    module_name = "wetserver"

    require_integration_opt_in()
    require_command_for_runtime("screen", runtime_backend=runtime_backend, module_name=module_name)

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itwetserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    run_and_assert_ok(env, server_name, "start")

    try:
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(log_path, ["ready", "started", "listening", "Done"], START_TIMEOUT)
        run_and_assert_ok(env, server_name, "status")
        wait_for_quake_ready("127.0.0.1", port, 300, log_path=log_path)

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout, query_result.stdout

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Players" in info_result.stdout, info_result.stdout

        import json as _info_json

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "quake", _info_data
        assert _info_data.get("players") == 0, _info_data
    finally:
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
