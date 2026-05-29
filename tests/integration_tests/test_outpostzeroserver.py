"""Integration test for outpostzeroserver."""

import json
import time

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    require_proton,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_udp_closed,
)
from gamemodules.outpostzeroserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: large SteamCMD payload under shared CI load
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600


def wait_for_info_protocol(env, server_name, expected_protocol, timeout_seconds, *, expected_port=None):
    """Poll ``info --json`` until the expected protocol is reported."""

    deadline = time.time() + timeout_seconds
    last_result = None
    last_payload = None
    while time.time() < deadline:
        result = run_alphagsm(env, server_name, "info", "--json")
        last_result = result
        if result.returncode == 0:
            try:
                payload = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                payload = None
            if payload is not None and payload.get("protocol") == expected_protocol:
                if expected_port is None or payload.get("port") == expected_port:
                    return payload
                last_payload = payload
            else:
                last_payload = payload
        time.sleep(5)
    payload_summary = repr(last_payload) if last_payload is not None else None
    stderr = "" if last_result is None else (last_result.stderr or last_result.stdout)
    pytest.fail(
        "info --json did not report protocol {!r} on port {!r} within {}s. "
        "Last payload: {}. Last command output: {}".format(
            expected_protocol,
            expected_port,
            timeout_seconds,
            payload_summary,
            stderr,
        )
    )


@pytest.mark.timeout(TEST_TIMEOUT)
def test_outpostzeroserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_proton()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itoutpostzeros"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "outpostzeroserver")

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = (
            install_dir
            / "WindowsServer"
            / "SurvivalGame"
            / "Saved"
            / "Logs"
            / "SurvivalGame.log"
        )
        wait_for_log_marker(
            log_path,
            ["Match State Changed from WaitingToStart to InProgress"],
            START_TIMEOUT,
        )

        # wait for query/info to become responsive
        info_payload = wait_for_info_protocol(
            env,
            server_name,
            "udp",
            START_TIMEOUT,
            expected_port=port,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "No further details available." in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == info_payload["protocol"], (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected game-port UDP readiness on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
