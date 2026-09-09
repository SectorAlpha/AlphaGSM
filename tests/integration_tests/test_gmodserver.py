"""Integration test for gmodserver."""

import json
import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_udp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    set_source_hibernation,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.gmodserver import _GMOD_CONTENT_INSTALLS, _GMOD_MOUNTDEPOTS_DEFAULTS, steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600


def _assert_common_gmod_info(data):
    assert data["players"] == 0, f"Expected 0 players on fresh server: {data!r}"
    assert data["bots"] == 0, f"Expected 0 bots on fresh server: {data!r}"
    assert data["map"] == "gm_construct", f"Expected gm_construct map: {data!r}"
    assert data["name"] == "AlphaGSM Garrys Mod", f"Unexpected Garry's Mod name: {data!r}"
    assert isinstance(data["folder"], str) and data["folder"], (
        f"Expected non-empty game folder: {data!r}"
    )
    assert isinstance(data["game"], str), f"Expected game string: {data!r}"
    assert isinstance(data["appid"], int) and data["appid"] > 0, (
        f"Expected positive appid: {data!r}"
    )
    assert data["max_players"] > 0, f"Expected positive max_players: {data!r}"


def _parse_keyvalue_file(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    mapping = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped in {'{', '}'} or stripped.startswith('"mountcfg"') or stripped.startswith('"gamedepotsystem"'):
            continue
        parts = stripped.split('"')
        if len(parts) >= 4:
            mapping[parts[1]] = parts[3]
    return mapping


def _assert_gmod_mount_files(install_dir):
    cfg_dir = install_dir / "garrysmod" / "cfg"
    mount_cfg_path = cfg_dir / "mount.cfg"
    mountdepots_path = cfg_dir / "mountdepots.txt"

    assert mount_cfg_path.exists(), f"Expected mount config to exist: {mount_cfg_path}"
    assert mountdepots_path.exists(), f"Expected mount depots config to exist: {mountdepots_path}"

    mount_cfg = _parse_keyvalue_file(mount_cfg_path)
    for mount_key, _app_id, game_dir in _GMOD_CONTENT_INSTALLS:
        expected_path = str(install_dir / "_gmod_content" / mount_key / game_dir)
        assert mount_cfg.get(mount_key) == expected_path, (
            f"Expected {mount_key!r} mount path {expected_path!r}, got {mount_cfg.get(mount_key)!r}"
        )
        assert (install_dir / "_gmod_content" / mount_key / game_dir).is_dir(), (
            f"Expected downloaded content directory for {mount_key!r}: "
            f"{install_dir / '_gmod_content' / mount_key / game_dir}"
        )

    mountdepots = _parse_keyvalue_file(mountdepots_path)
    for depot_name in _GMOD_MOUNTDEPOTS_DEFAULTS:
        assert mountdepots.get(depot_name) == "1", (
            f"Expected mount depot {depot_name!r} to be enabled: {mountdepots!r}"
        )


def test_gmodserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name="gmodserver",
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itgmodserver"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name="gmodserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "gmodserver")

    # setup
    result = run_and_assert_ok(
        env,
        server_name,
        "setup",
        "-n",
        str(port),
        str(install_dir),
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    server_cfg_path = install_dir / "garrysmod" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()
    _assert_gmod_mount_files(install_dir)
    set_source_hibernation(server_cfg_path, enabled=False)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        _assert_common_gmod_info(info_data)

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
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == port, (
            f"Expected A2S query port {port}: {_info_data!r}"
        )
        _assert_common_gmod_info(_info_data)
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
