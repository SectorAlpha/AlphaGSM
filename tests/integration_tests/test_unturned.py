"""Integration test for unturned."""

import json
import os
import sys

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
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_udp_closed,
    resolve_steamcmd_linux_runtime_image,
    wait_for_log_marker,
)
from gamemodules.unturned import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "unturned"
WORKSHOP_MAP_ID = "2396897717"
WORKSHOP_MAP_NAME = "PEI Arena"


def test_unturned_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itunturned"

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
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=port)
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
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)

    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)


@pytest.mark.skipif(
    os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for public Workshop download/load validation",
)
@pytest.mark.parametrize("workshop_runtime_backend", ["process", "docker"])
def test_unturned_workshop_map_lifecycle(tmp_path, workshop_runtime_backend):
    """The fresh running engine must report a Workshop-only map through A2S."""
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime("screen", runtime_backend=workshop_runtime_backend,
                                module_name=module_name)
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itunturnedworkshop"
    write_config(config_path, home_dir, session_tag="AlphaGSM-Workshop-IT#",
                 runtime_backend=workshop_runtime_backend, module_name=module_name)
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    run_and_assert_ok(env, server_name, "create", module_name)
    if workshop_runtime_backend == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    # A brand-new install must not have a built-in copy of this retired arena map.
    assert not (install_dir / "Maps" / WORKSHOP_MAP_NAME).exists()
    run_and_assert_ok(env, server_name, "mod", "add", "workshop", WORKSHOP_MAP_ID)
    run_and_assert_ok(env, server_name, "mod", "apply")
    commands = install_dir / "Servers" / server_name / "Server" / "Commands.dat"
    with commands.open("a", encoding="utf-8") as handle:
        handle.write("Map " + WORKSHOP_MAP_NAME + "\n")

    run_and_assert_ok(env, server_name, "start")
    try:
        wait_for_log_marker(install_dir / "Logs" / ("Server_" + server_name + ".log"),
                            ["Loading level: 100%"], START_TIMEOUT)
        wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT, expected_port=port)
        run_and_assert_ok(env, server_name, "status")
        query = run_and_assert_ok(env, server_name, "query")
        assert "Server is responding" in query.stdout
        info = run_and_assert_ok(env, server_name, "info")
        assert WORKSHOP_MAP_NAME in info.stdout
        info_json = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json.stdout.strip())
        assert info_data["protocol"] == "a2s"
        assert info_data["map"] == WORKSHOP_MAP_NAME, (
            "The running Unturned engine did not load the Workshop-only map: " + repr(info_data)
        )
        assert info_data["players"] == 0
    finally:
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1],
                                           timeout=STOP_TIMEOUT)
    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)

    run_and_assert_ok(env, server_name, "mod", "remove", "workshop", WORKSHOP_MAP_ID)
    run_and_assert_ok(env, server_name, "mod", "apply")
    workshop_config = install_dir / "Servers" / server_name / "WorkshopDownloadConfig.json"
    assert int(WORKSHOP_MAP_ID) not in json.loads(workshop_config.read_text())["File_IDs"]
