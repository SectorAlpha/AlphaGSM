"""Integration test for ss14server.

ENABLED (BYO): supply a direct Linux x64 server archive while the official
Wizard's Den build feed publishes no server builds.
"""

import os

from utils.valve_server import detect_query_host

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_info_protocol,
    wait_for_tcp_closed,
)

pytestmark = [
    pytest.mark.integration,
]

START_TIMEOUT = 600
STOP_TIMEOUT = 90
BYO_SKIP_REASON = (
    "ENABLED (BYO): set ALPHAGSM_SS14_SERVER_URL to a direct Linux x64 "
    "Space Station 14 server archive while the Wizard's Den build feed "
    "publishes no server builds"
)


def test_ss14server_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "ss14server"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    require_command_for_runtime(
        "dotnet",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itss14server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)

    # setup
    setup_args = [server_name, "setup", "-n", str(port), str(install_dir)]
    server_url = os.environ.get("ALPHAGSM_SS14_SERVER_URL", "").strip()
    if server_url:
        setup_args.extend(["-u", server_url])
    result = run_alphagsm(env, *setup_args)
    log_command_result("alphagsm " + " ".join(setup_args), result)
    if result.returncode != 0:
        combined_output = "\n".join(
            part for part in (result.stdout, result.stderr) if part
        )
        if not server_url and "ENABLED (BYO):" in combined_output:
            pytest.skip(BYO_SKIP_REASON)
        skip_for_known_steamcmd_issue(result)
    assert result.returncode == 0, result.stderr or result.stdout

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["Ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        robust_info = wait_for_info_protocol(env, server_name, "robust_status", START_TIMEOUT)
        assert robust_info.get("players") == 0, (
            f"Expected 0 players once SS14 status API is ready: {robust_info!r}"
        )

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players     : 0" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "robust_status", (
            f"Expected robust_status protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed(detect_query_host(), port, STOP_TIMEOUT)
