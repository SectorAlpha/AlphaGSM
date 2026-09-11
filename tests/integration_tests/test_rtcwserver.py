"""Integration test for rtcwserver."""

import os

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
    wait_for_runtime_log_marker,
    wait_for_tcp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
RTCW_REQUIRED_MULTIPLAYER_ASSETS = (
    "mp_bin.pk3",
    "mp_pak0.pk3",
    "mp_pak1.pk3",
    "mp_pak2.pk3",
    "mp_pak3.pk3",
    "mp_pak4.pk3",
    "mp_pak5.pk3",
    "mp_pakmaps0.pk3",
    "mp_pakmaps1.pk3",
    "mp_pakmaps2.pk3",
    "mp_pakmaps3.pk3",
    "mp_pakmaps4.pk3",
    "mp_pakmaps5.pk3",
    "mp_pakmaps6.pk3",
)
BYO_SKIP_REASON = (
    "ENABLED (BYO): requires original RTCW multiplayer assets "
    "(main/mp_bin.pk3, mp_pak*.pk3, mp_pakmaps*.pk3)"
)


def test_rtcwserver_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "rtcwserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itrtcwserver"

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
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        result,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)
    assert result.returncode == 0, result.stderr or result.stdout

    main_dir = install_dir / "main"
    missing_assets = [
        asset_name
        for asset_name in RTCW_REQUIRED_MULTIPLAYER_ASSETS
        if not (main_dir / asset_name).is_file()
    ]
    if missing_assets:
        pytest.skip(
            f"{BYO_SKIP_REASON}; missing staged assets under {main_dir}: "
            + ", ".join(missing_assets)
        )

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["ready", "started", "listening", "Done"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

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
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
