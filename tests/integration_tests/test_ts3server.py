"""Integration test for ts3server."""

import json as _info_json
import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_command_for_runtime,
    default_runtime_backend,
    pick_free_tcp_port,
    wait_for_tcp_open,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_ts3server_lifecycle(tmp_path):
    require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "ts3server"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itts3server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()
    queryport = pick_free_tcp_port()
    while queryport == port:
        queryport = pick_free_tcp_port()
    filetransferport = pick_free_tcp_port()
    while filetransferport in {port, queryport}:
        filetransferport = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))
    run_and_assert_ok(env, server_name, "set", "filetransferport", str(filetransferport))

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness — TS3 prints "ServerQuery created" once the query port is live
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["ServerQuery created", "TeamSpeak 3 Server started", "listening", "started"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # TS3 ServerQuery runs on the configured TCP query port; wait until it is accepting
        wait_for_tcp_open("127.0.0.1", queryport, 300, log_path=log_path)

        # query — TS3 ServerQuery protocol
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info — human-readable TS3 info (channels shown as count + hint without --detailed)
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Clients  :" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )
        assert "--detailed" in info_result.stdout, (
            f"Expected --detailed hint in info text output: {info_result.stdout!r}"
        )

        # info --detailed — channel list shown in text
        info_det_text = run_and_assert_ok(env, server_name, "info", "--detailed")
        assert "Channels :" in info_det_text.stdout, (
            f"Expected Channels line with --detailed: {info_det_text.stdout!r}"
        )

        # info --json — full TS3 property verification (channels omitted without --detailed)
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "ts3", (
            f"Expected ts3 protocol in info JSON: {_info_data!r}"
        )
        assert isinstance(_info_data["name"], str) and _info_data["name"], (
            f"Expected non-empty server name: {_info_data!r}"
        )
        assert isinstance(_info_data["clients_online"], int), (
            f"Expected clients_online integer: {_info_data!r}"
        )
        # TS3 counts authenticated ServerQuery connections as clients, so a
        # freshly started server may report 0 or 1 depending on timing.
        assert _info_data["clients_online"] <= 1, (
            f"Expected 0-1 clients on fresh server (SQ admin counts): {_info_data!r}"
        )
        assert isinstance(_info_data["max_clients"], int) and _info_data["max_clients"] > 0, (
            f"Expected positive max_clients: {_info_data!r}"
        )
        assert isinstance(_info_data["uptime"], int), (
            f"Expected uptime integer: {_info_data!r}"
        )
        assert isinstance(_info_data["platform"], str) and _info_data["platform"], (
            f"Expected non-empty platform string: {_info_data!r}"
        )
        assert isinstance(_info_data["version"], str) and _info_data["version"], (
            f"Expected non-empty version string: {_info_data!r}"
        )
        assert "channels" not in _info_data, (
            f"channels list should be omitted without --detailed: {_info_data!r}"
        )
        assert isinstance(_info_data["channels_count"], int), (
            f"Expected channels_count integer in summary JSON: {_info_data!r}"
        )

        # info --json --detailed — full channel list included
        info_detailed_result = run_and_assert_ok(
            env, server_name, "info", "--json", "--detailed"
        )
        _info_det = _info_json.loads(info_detailed_result.stdout.strip())
        assert isinstance(_info_det["channels"], list) and len(_info_det["channels"]) > 0, (
            f"Expected non-empty channels list with --detailed (TS3 always has Default Channel):"
            f" {_info_det!r}"
        )
        assert all(isinstance(ch.get("name"), str) for ch in _info_det["channels"]), (
            f"Expected all channels to have name strings: {_info_det!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
    wait_for_tcp_closed("127.0.0.1", queryport, STOP_TIMEOUT)
    wait_for_tcp_closed("127.0.0.1", filetransferport, STOP_TIMEOUT)
