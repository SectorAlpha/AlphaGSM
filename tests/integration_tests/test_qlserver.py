"""Integration test for qlserver."""

import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_quake_ready,
    wait_for_tcp_closed,
)
from gamemodules.qlserver import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
BYO_SKIP_REASON = (
    "ENABLED (BYO): Quake Live installs qzeroded.x64, but anonymous SteamCMD startup still "
    "exits immediately; this lane needs an owned/authenticated Quake Live "
    "entitlement plus any required server auth/config"
)

def test_qlserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "qlserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itqlserver"

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
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result("alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))), result)
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    assert result.returncode == 0, result.stderr or result.stdout

    # start
    start_result = run_alphagsm(env, server_name, "start")
    log_command_result("alphagsm " + " ".join((server_name, "start")), start_result)
    if start_result.returncode != 0:
        skip_for_known_steamcmd_issue(start_result, app_id=steam_app_id)
        if (install_dir / "qzeroded.x64").is_file():
            snippet = "\n".join(
                part for part in (start_result.stdout, start_result.stderr) if part
            )[:300].replace("\n", " | ")
            pytest.skip(f"{BYO_SKIP_REASON}: {snippet}")
    assert start_result.returncode == 0, start_result.stderr or start_result.stdout

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # Quake Live uses the Quake UDP status protocol, not A2S
        wait_for_quake_ready("127.0.0.1", port, 300, log_path=log_path)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "quake", (
            f"Expected quake protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
