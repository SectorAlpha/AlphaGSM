"""Integration test for bb2server."""

import json
import os
import time
import uuid

from tests.smoke_tests.nwi_workshop import assert_native_mounts

import pytest

from conftest import (
    configure_steamcmd_path,
    workshop_runtime_backends,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    default_runtime_backend,
    require_command_for_runtime,
    pick_free_tcp_port_group,
    effective_runtime_backend,
    resolve_steamcmd_linux_runtime_image,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    find_source_server_cfg,
    set_source_hibernation,
    assert_source_server_empty,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)
from gamemodules.bb2server import steam_app_id

pytestmark = [pytest.mark.integration]

START_TIMEOUT = 600
STOP_TIMEOUT = 90


def test_bb2server_lifecycle(tmp_path, workshop_source=None, workshop_identifier=None, runtime_backend=None):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "bb2server"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = f"workshop-bb2server-{runtime_backend}" if workshop_source else "itbb2server"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    if workshop_source:
        steamcmd_path = os.environ.get("ALPHAGSM_BB2SERVER_STEAMCMD_PATH", str(tmp_path / "steamcmd"))
        configure_steamcmd_path(config_path, steamcmd_path)
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(3)

    # create
    run_and_assert_ok(env, server_name, "create", "bb2server")
    run_and_assert_ok(env, server_name, "set", "clientport", str(port + 1))
    run_and_assert_ok(env, server_name, "set", "sourcetvport", str(port + 2))

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    server_cfg_path = find_source_server_cfg(install_dir)
    set_source_hibernation(server_cfg_path, enabled=False)

    item_ids = []
    if effective_runtime_backend(runtime_backend, module_name=module_name) == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    if workshop_source:
        operator_file = install_dir / "brainbread2" / "maps" / "alphagsm-operator.txt"
        operator_file.write_text("AlphaGSM test-owned operator asset\n")
        run_and_assert_ok(env, server_name, "mod", "add", workshop_source, workshop_identifier)
        run_and_assert_ok(env, server_name, "mod", "apply")
        data = json.loads((home_dir / "conf" / f"{server_name}.json").read_text())
        item_ids = [entry["workshop_id"] for entry in data["mods"]["desired"]["workshop"]]
        assert item_ids
        owned_paths = list(data["mods"]["owned_payloads"]["bb2server_workshop_maps"])
        assert owned_paths

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        info_data = wait_for_info_protocol(
            env, server_name, "a2s", START_TIMEOUT, expected_port=port
        )
        assert_source_server_empty(info_data)
        if item_ids:
            _verify_workshop_load(env, server_name, item_ids, port)

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

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == port, (
            f"Expected A2S query port {port}: {_info_data!r}"
        )
        assert_source_server_empty(_info_data)
    finally:
        # stop
        stop_result = run_alphagsm(env, server_name, "stop")
        log_command_result("alphagsm stop", stop_result)

    assert stop_result.returncode == 0, stop_result.stderr or stop_result.stdout
    # verify stopped
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
    if item_ids:
        run_and_assert_ok(env, server_name, "mod", "cleanup")
        assert all(not (install_dir / relative).exists() for relative in owned_paths)
        assert operator_file.read_text() == "AlphaGSM test-owned operator asset\n"
        assert not list((install_dir / "brainbread2" / "workshop" / "content" / "346330").glob(f"*/maps/{_workshop_map_name()}.bsp"))



@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_BB2SERVER_WORKSHOP") != "1",
                    reason="Opt in to external native Workshop lifecycle validation")
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_bb2server_workshop_loads(tmp_path, runtime_backend):
    identifier = os.environ.get("ALPHAGSM_BB2SERVER_WORKSHOP_COLLECTION")
    source = "workshop-collection" if identifier else "workshop"
    identifier = identifier or os.environ.get("ALPHAGSM_BB2SERVER_WORKSHOP_ITEM", "710060895")
    test_bb2server_lifecycle(tmp_path, source, identifier, runtime_backend)


def _workshop_map_name():
    return os.environ.get("ALPHAGSM_BB2SERVER_WORKSHOP_MAP", "bbc_frozenheart")


def _verify_workshop_load(env, server_name, item_ids, port):
    """Require the running engine to execute the selected custom BSP via real A2S."""
    token = "AlphaGSM-bb2server-" + uuid.uuid4().hex
    run_and_assert_ok(env, server_name, "send", f"echo BEGIN-{token}; path; echo END-{token}")
    deadline, output, error = time.monotonic() + 600, "", None
    while time.monotonic() < deadline:
        output = run_and_assert_ok(env, server_name, "logs", "-n", "20000").stdout
        try:
            assert_native_mounts(output, 346330, item_ids, token)
            break
        except AssertionError as exc:
            error = exc
        time.sleep(2)
        if str(error).startswith("Running engine did not mount"):
            token = "AlphaGSM-bb2server-" + uuid.uuid4().hex
            run_and_assert_ok(env, server_name, "send", f"echo BEGIN-{token}; path; echo END-{token}")
    else:
        pytest.fail(f"Native Workshop mount verification failed: {error}\n{output[-20000:]}")
    map_name = _workshop_map_name()
    assert map_name and all(character.isalnum() or character in "_-" for character in map_name)
    run_and_assert_ok(env, server_name, "send", f"changelevel {map_name}")
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        result = run_alphagsm(env, server_name, "info", "--json")
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout.strip())
                if data.get("protocol") == "a2s" and data.get("map") == map_name and data.get("port") == port:
                    print(f"ENGINE_WORKSHOP_MAP_LOADED {map_name} app=346330 items={item_ids}")
                    return
            except ValueError:
                pass
        time.sleep(2)
    output = run_and_assert_ok(env, server_name, "logs", "-n", "20000").stdout
    pytest.fail(f"Running engine did not load Workshop map {map_name}\n{output[-20000:]}")
