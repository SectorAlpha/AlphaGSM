"""Integration test for ts3server."""

import json as _info_json

import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 300
STOP_TIMEOUT = 90


def test_ts3server_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itts3server"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "ts3server")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness — TS3 prints "ServerQuery created" once the query port is live
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["ServerQuery created", "TeamSpeak 3 Server started", "listening", "started"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query — TS3 ServerQuery protocol
        query_result = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info — human-readable TS3 info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert "Clients  :" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json — full TS3 property verification
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
        assert _info_data["clients_online"] == 0, (
            f"Expected 0 clients on fresh server: {_info_data!r}"
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
        assert isinstance(_info_data["channels"], list) and len(_info_data["channels"]) > 0, (
            f"Expected non-empty channels list (TS3 always has Default Channel): {_info_data!r}"
        )
        assert all(isinstance(ch.get("name"), str) for ch in _info_data["channels"]), (
            f"Expected all channels to have name strings: {_info_data!r}"
        )
    finally:
        # stop
        run_and_assert_ok(env, server_name, "stop")

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
