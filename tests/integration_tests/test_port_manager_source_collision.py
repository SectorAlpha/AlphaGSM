"""Integration coverage for Source server port-manager collisions."""

import json
from pathlib import Path

import pytest

from conftest import (
    require_command,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_alphagsm,
    run_and_assert_ok,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_a2s_ready,
    wait_for_udp_closed,
    find_source_server_cfg,
    set_source_hibernation,
    read_info_json,
    assert_source_server_empty,
)
from gamemodules.counterstrikeglobaloffensive import steam_app_id as csgo_steam_app_id
from gamemodules.teamfortress2 import steam_app_id as tf2_steam_app_id
from utils.valve_server import detect_query_host

pytestmark = pytest.mark.integration

TEST_TIMEOUT = 1200
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _run_setup(env, server_name, port, install_dir):
    result = run_alphagsm(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=TEST_TIMEOUT,
    )
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        result,
    )
    return result


def _skip_for_known_tf2_setup_issue(result):
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "tf/cfg/server.cfg",
        "No such file or directory",
        f"Failed to install app '{tf2_steam_app_id}' (Missing configuration)",
    )
    if all(marker in combined for marker in known_markers):
        pytest.skip(
            "TF2 setup currently fails during install/config creation "
            "(missing tf/cfg/server.cfg after SteamCMD setup)"
        )


def _skip_for_known_csgo_runtime_issue(result):
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "is currently disabled",
        "libgcc_s.so.1",
        "GCC_7.0.0",
    )
    for marker in known_markers:
        if marker in combined:
            pytest.skip(
                "Counter-Strike server is not currently runnable in CI/runtime: "
                + marker
            )


def _rewrite_server_port(home_dir, server_name, port):
    data_path = Path(home_dir) / "conf" / f"{server_name}.json"
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    payload["port"] = int(port)
    data_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _set_tf2_hibernation(server_cfg_path, enabled):
    cfg_text = Path(server_cfg_path).read_text(encoding="utf-8")
    target = "tf_allow_server_hibernation 0"
    replacement = "tf_allow_server_hibernation 1" if enabled else target
    if enabled:
        if target in cfg_text:
            cfg_text = cfg_text.replace(target, replacement)
        elif replacement not in cfg_text:
            cfg_text += "\ntf_allow_server_hibernation 1\n"
    else:
        cfg_text = cfg_text.replace("tf_allow_server_hibernation 1", target)
        if target not in cfg_text:
            cfg_text += "\ntf_allow_server_hibernation 0\n"
    Path(server_cfg_path).write_text(cfg_text, encoding="utf-8")


def _force_source_server_awake(server_cfg_path, *, tf2=False):
    set_source_hibernation(server_cfg_path, enabled=False)
    if tf2:
        _set_tf2_hibernation(server_cfg_path, enabled=False)


def _wait_for_a2s_info(env, server_name, query_host, port):
    log_path = None
    result = run_and_assert_ok(env, server_name, "status")
    assert "Server is running" in result.stdout
    wait_for_a2s_ready(query_host, port, START_TIMEOUT, log_path=log_path)
    query_result = run_and_assert_ok(env, server_name, "query")
    assert "Server is responding" in query_result.stdout
    info_result = run_and_assert_ok(env, server_name, "info")
    assert "Players     : 0/" in info_result.stdout
    info_json = read_info_json(env, server_name)
    assert info_json["protocol"] == "a2s", f"Expected a2s info output: {info_json!r}"
    assert_source_server_empty(info_json)
    return info_json


def _pick_distinct_port(first_port):
    while True:
        candidate = pick_free_tcp_port()
        if candidate != first_port:
            return candidate


def test_source_servers_only_both_run_after_one_changes_port(tmp_path):
    """Two Source servers should not both run on one port until one changes it."""

    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    config_path = tmp_path / "alphagsm.conf"
    tf2_dir = tmp_path / "tf2-server"
    csgo_dir = tmp_path / "csgo-server"
    tf2_server = "itpmtf2srv"
    csgo_server = "itpmcsgosrv"
    shared_port = pick_free_tcp_port()
    shifted_port = _pick_distinct_port(shared_port)
    query_host = detect_query_host()

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)

    run_and_assert_ok(env, tf2_server, "create", "teamfortress2")
    tf2_setup = _run_setup(env, tf2_server, shared_port, tf2_dir)
    skip_for_known_steamcmd_issue(tf2_setup, app_id=tf2_steam_app_id)
    _skip_for_known_tf2_setup_issue(tf2_setup)
    assert tf2_setup.returncode == 0, tf2_setup.stderr or tf2_setup.stdout

    run_and_assert_ok(env, csgo_server, "create", "counterstrikeglobaloffensive")
    csgo_setup = _run_setup(env, csgo_server, shifted_port, csgo_dir)
    skip_for_known_steamcmd_issue(csgo_setup, app_id=csgo_steam_app_id)
    _skip_for_known_csgo_runtime_issue(csgo_setup)
    assert csgo_setup.returncode == 0, csgo_setup.stderr or csgo_setup.stdout

    _force_source_server_awake(find_source_server_cfg(tf2_dir), tf2=True)
    _force_source_server_awake(find_source_server_cfg(csgo_dir))

    _rewrite_server_port(home_dir, csgo_server, shared_port)

    tf2_started = False
    csgo_started = False
    try:
        run_and_assert_ok(env, tf2_server, "start", timeout=60)
        tf2_started = True
        tf2_info = _wait_for_a2s_info(env, tf2_server, query_host, shared_port)
        assert "Team Fortress" in (tf2_info.get("game") or ""), (
            f"Expected Team Fortress details in TF2 info: {tf2_info!r}"
        )

        blocked = run_alphagsm(env, csgo_server, "start", timeout=60)
        log_command_result("alphagsm " + " ".join((csgo_server, "start")), blocked)
        _skip_for_known_csgo_runtime_issue(blocked)
        assert blocked.returncode != 0
        combined = "\n".join(part for part in (blocked.stdout, blocked.stderr) if part)
        assert "claimed ports are not free" in combined
        assert tf2_server in combined

        run_and_assert_ok(env, csgo_server, "set", "port", str(shifted_port))

        run_and_assert_ok(env, csgo_server, "start", timeout=60)
        csgo_started = True
        csgo_info = _wait_for_a2s_info(env, csgo_server, query_host, shifted_port)
        assert csgo_info.get("protocol") == "a2s"
    finally:
        if csgo_started:
            log_command_result(
                "alphagsm " + " ".join((csgo_server, "stop")),
                run_alphagsm(env, csgo_server, "stop", timeout=STOP_TIMEOUT),
            )
            wait_for_udp_closed(query_host, shifted_port, STOP_TIMEOUT)
        if tf2_started:
            log_command_result(
                "alphagsm " + " ".join((tf2_server, "stop")),
                run_alphagsm(env, tf2_server, "stop", timeout=STOP_TIMEOUT),
            )
            wait_for_udp_closed(query_host, shared_port, STOP_TIMEOUT)
