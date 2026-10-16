"""Integration test for btserver."""

import os
from pathlib import Path
import shutil
import sys

import pytest

from conftest import (
    workshop_runtime_backends,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    default_runtime_backend,
    effective_runtime_backend,
    pick_free_tcp_port_group,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_info_protocol,
    wait_for_generic_udp_closed,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    resolve_steamcmd_linux_runtime_image,
)
from gamemodules.btserver import steam_app_id
from tests.smoke_tests.btserver_workshop import FIXTURE_ID, FIXTURE_NAME, assert_workshop_loaded

pytestmark = pytest.mark.integration

START_TIMEOUT = 1800
LOCAL_DOCKER_IMAGE = "alphagsm-steamcmd-linux-runtime:test"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-steamcmd-linux-runtime:latest"


@pytest.mark.timeout(3600)  # 60 min: SteamCMD download + slow SteamManager initialisation
def test_btserver_lifecycle(tmp_path, runtime_backend=None, workshop_fixture=False):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "btserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itbt" + tmp_path.name.replace("_", "")[-8:])[:15]
    image = resolve_steamcmd_linux_runtime_image()

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
    if effective_runtime_backend(runtime_backend, module_name=module_name) == "docker":
        run_and_assert_ok(env, server_name, "set", "image", image)
    cache = os.environ.get("ALPHAGSM_BTSERVER_TEST_CACHE")
    if cache:
        source = Path(cache).expanduser().resolve()
        assert (source / "DedicatedServer").is_file()
        shutil.copytree(source, install_dir, ignore=shutil.ignore_patterns(".alphagsm", "LocalMods", "steamapps", "config_player.xml", "serversettings.xml"))

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop",
                          f"https://steamcommunity.com/sharedfiles/filedetails/?id={FIXTURE_ID}")
        run_and_assert_ok(env, server_name, "mod", "apply")

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

        # Wait on AlphaGSM's declared info surface rather than a raw guessed socket.
        wait_for_info_protocol(env, server_name, "udp", 900)
        if workshop_fixture:
            run_and_assert_ok(env, server_name, "send", f"calculatehashes {FIXTURE_NAME}")
            run_and_assert_ok(env, server_name, "send", "items")
            evidence = wait_for_runtime_log_marker(env, server_name, ["- Welding Table"], 90)
            assert_workshop_loaded(evidence)
            if os.environ.get("ALPHAGSM_WORK_DIR"):
                evidence_dir = Path(os.environ["ALPHAGSM_WORK_DIR"]) / "evidence"
                evidence_dir.mkdir(exist_ok=True)
                (evidence_dir / f"btserver-{runtime_backend}.log").write_text(evidence)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "UDP ping on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "No further details available." in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected game port {port} in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=90)
    assert_alphagsm_result_ok(stop_result)
    final_status = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in final_status.stdout
    wait_for_generic_udp_closed("127.0.0.1", port, 90)
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "cleanup")
        assert FIXTURE_NAME not in (install_dir / "config_player.xml").read_text()


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for public Workshop load checks")
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_btserver_native_workshop(tmp_path, runtime_backend):
    test_btserver_lifecycle(tmp_path, runtime_backend, workshop_fixture=True)
