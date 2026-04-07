"""Integration test for cssserver."""

import json
import time

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_a2s_ready,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.cssserver import steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _wait_for_info_protocol(env, server_name, expected_protocol, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_result = None
    last_data = None
    while time.time() < deadline:
        result = run_alphagsm(env, server_name, "info", "--json", timeout=120)
        last_result = result
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                data = None
            else:
                last_data = data
                if data.get("protocol") == expected_protocol:
                    return data
        time.sleep(5)

    log_command_result(
        "alphagsm " + " ".join((server_name, "info", "--json")),
        last_result,
    )
    pytest.fail(
        f"cssserver info --json never returned protocol {expected_protocol!r} within {timeout_seconds}s: "
        f"last payload={last_data!r}"
    )


def _set_source_hibernation(server_cfg_path, enabled):
    cfg_text = server_cfg_path.read_text(encoding="utf-8")
    target = "sv_hibernate_when_empty 0"
    replacement = "sv_hibernate_when_empty 1" if enabled else target
    if enabled:
        if target in cfg_text:
            cfg_text = cfg_text.replace(target, replacement)
        elif replacement not in cfg_text:
            cfg_text += "\nsv_hibernate_when_empty 1\n"
    else:
        cfg_text = cfg_text.replace("sv_hibernate_when_empty 1", target)
        if target not in cfg_text:
            cfg_text += "\nsv_hibernate_when_empty 0\n"
    server_cfg_path.write_text(cfg_text, encoding="utf-8")


def _assert_common_css_info(data):
    assert data.get("players") == 0, f"Expected 0 players on fresh server: {data!r}"
    assert data.get("bots") == 0, f"Expected 0 bots on fresh server: {data!r}"
    assert data.get("map") == "de_dust2", f"Expected de_dust2 map: {data!r}"
    assert data.get("name") == "AlphaGSM Counter-Strike: Source", (
        f"Unexpected CSS name: {data!r}"
    )


def test_cssserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itcssserver"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    query_host = detect_query_host()

    # create
    run_and_assert_ok(env, server_name, "create", "cssserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    server_cfg_path = install_dir / "cstrike" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()
    _set_source_hibernation(server_cfg_path, enabled=True)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"
        wait_for_log_marker(
            log_path,
            ["SV_ActivateServer", "ready"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        hibernating_info = run_and_assert_ok(env, server_name, "info", "--json")
        hibernating_info = json.loads(hibernating_info.stdout.strip())
        assert hibernating_info["protocol"] in {"console", "a2s"}, (
            f"Expected console or a2s info after startup: {hibernating_info!r}"
        )
        _assert_common_css_info(hibernating_info)

        if hibernating_info["protocol"] != "a2s":
            awake_info = _wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)
            _assert_common_css_info(awake_info)

        wait_for_a2s_ready(query_host, port, 600, log_path=log_path)

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
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        _assert_common_css_info(_info_data)
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed(query_host, port, STOP_TIMEOUT)
