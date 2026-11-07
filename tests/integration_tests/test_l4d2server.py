"""Integration test for l4d2server."""

import json
import os
from pathlib import Path
import shutil
import time
from uuid import uuid4

import pytest

from conftest import (
    workshop_runtime_backends,
    default_runtime_backend,
    effective_runtime_backend,
    resolve_steamcmd_linux_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port_group,
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
from gamemodules.l4d2server import steam_app_id
from tests.smoke_tests.l4d2_workshop import BEGIN_MARKER, END_MARKER, assert_workshop_mounts

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _assert_common_l4d2_info(data):
    assert data.get("players") == 0, f"Expected 0 players on fresh server: {data!r}"
    assert data.get("bots") == 0, f"Expected 0 bots on fresh server: {data!r}"
    assert data.get("map") == "c5m1_waterfront", f"Expected c5m1_waterfront map: {data!r}"
    assert data.get("name") == "AlphaGSM Left 4 Dead 2", f"Unexpected L4D2 name: {data!r}"


def test_l4d2server_lifecycle(tmp_path, collection_id=None, runtime_backend=None, item_id=None):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    module_name = "l4d2server"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    depot_cache = os.environ.get("ALPHAGSM_L4D2_TEST_CACHE")
    if depot_cache:
        # Preserve stock engine configs such as valve.rc; recreate server.cfg and addon state.
        shutil.copytree(Path(depot_cache), install_dir,
                        ignore=shutil.ignore_patterns(".alphagsm", "addons", "server.cfg"))
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itl4d2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(2)

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "clientport", str(port + 1))
    run_and_assert_ok(env, server_name, "workshop", "list")

    workshop_ids = []
    if item_id:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", item_id)
    if collection_id:
        # Validate public collection metadata before downloading the server depots.
        run_and_assert_ok(env, server_name, "mod", "add", "workshop-collection", collection_id)
    if collection_id or item_id:
        store = json.loads((home_dir / "conf" / f"{server_name}.json").read_text())
        workshop_ids = [entry["workshop_id"] for entry in store["mods"]["desired"]["workshop"]]
        assert workshop_ids, "Collection must contain downloadable L4D2 items"

    # setup
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        "alphagsm " + " ".join((server_name, "setup", "-n", str(port), str(install_dir))),
        result,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    assert result.returncode == 0, f"setup failed: {result.stderr or result.stdout}"
    if effective_runtime_backend(runtime_backend, module_name=module_name) == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())

    server_cfg_path = install_dir / "left4dead2" / "cfg" / "server.cfg"
    assert server_cfg_path.exists()
    set_source_hibernation(server_cfg_path, enabled=False)

    if collection_id or item_id:
        run_and_assert_ok(env, server_name, "mod", "apply", timeout=1800)
        for item_id in workshop_ids:
            addon = install_dir / "left4dead2" / "addons" / "workshop" / f"{item_id}.vpk"
            assert addon.is_file() and addon.stat().st_size > 0, f"Missing installed addon {addon}"

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        _assert_common_l4d2_info(info_data)
        if collection_id or item_id:
            _verify_workshop_loaded(env, server_name, workshop_ids)

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
        _assert_common_l4d2_info(_info_data)
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)


@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_l4d2server_workshop_collection_loads(tmp_path, runtime_backend):
    """Load a popular public campaign collection and independent server addon."""
    require_integration_opt_in()
    if os.environ.get("ALPHAGSM_RUN_L4D2_WORKSHOP") != "1":
        pytest.skip("Set ALPHAGSM_RUN_L4D2_WORKSHOP=1 for the external Workshop collection load test")
    collection_id = os.environ.get(
        "ALPHAGSM_L4D2_WORKSHOP_COLLECTION",
        "https://steamcommunity.com/sharedfiles/filedetails/?id=121115793",
    )
    item_id = os.environ.get(
        "ALPHAGSM_L4D2_WORKSHOP_ITEM",
        "https://steamcommunity.com/sharedfiles/filedetails/?id=214630948",
    )
    test_l4d2server_lifecycle(tmp_path, collection_id=collection_id,
                            runtime_backend=runtime_backend, item_id=item_id)


def _verify_workshop_loaded(env, server_name, item_ids):
    """Probe the running server through AlphaGSM console commands and console logs."""
    nonce = uuid4().hex
    begin_marker, end_marker = f"{BEGIN_MARKER}-{nonce}", f"{END_MARKER}-{nonce}"
    run_and_assert_ok(env, server_name, "send", f"echo {begin_marker}")
    run_and_assert_ok(env, server_name, "send", "show_addon_load_order")
    run_and_assert_ok(env, server_name, "send", f"echo {end_marker}")
    deadline = time.monotonic() + 60
    last_output = ""
    last_error = None
    while time.monotonic() < deadline:
        last_output = run_and_assert_ok(env, server_name, "logs", "-n", "20000").stdout
        try:
            assert_workshop_mounts(last_output, item_ids, begin_marker=begin_marker, end_marker=end_marker)
            return
        except AssertionError as exc:
            last_error = exc
        time.sleep(1)
    pytest.fail(f"L4D2 Workshop load verification failed: {last_error}\n{last_output[-20000:]}")
