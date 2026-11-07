"""Integration test for projectzomboid."""

import os
from pathlib import Path
import shutil
import sys

import pytest

from conftest import (
    workshop_runtime_backends,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    default_runtime_backend,
    effective_runtime_backend,
    require_command_for_runtime,
    resolve_steamcmd_linux_runtime_image,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    skip_for_known_steamcmd_issue,
    wait_for_runtime_log_marker,
    wait_for_info_protocol,
    wait_for_udp_closed,
)
from gamemodules.projectzomboid import steam_app_id
from tests.smoke_tests.projectzomboid_workshop import FIXTURE_ID, assert_workshop_loaded

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90


@pytest.mark.timeout(3600)
def test_projectzomboid_lifecycle(tmp_path, runtime_backend=None, workshop_fixture=False):
    if runtime_backend is None:
        runtime_backend = os.environ.get(
            "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
        )
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = "projectzomboid"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itprojectzombo"

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

    if effective_runtime_backend(runtime_backend, module_name=module_name) == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    cache = os.environ.get("ALPHAGSM_PROJECTZOMBOID_TEST_CACHE")
    if cache:
        source = Path(cache).expanduser().resolve()
        assert (source / "start-server.sh").is_file(), "PZ test cache needs an installed dedicated server"
        # Copy immutable install files, not the cache's mutable worlds or manager state.
        shutil.copytree(source, install_dir, ignore=shutil.ignore_patterns("Zomboid", ".alphagsm", "workshop"))

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    query_port = pick_free_tcp_port()
    run_and_assert_ok(env, server_name, "set", "queryport", str(query_port))
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", FIXTURE_ID)
        run_and_assert_ok(env, server_name, "mod", "apply")
        configuration = (install_dir / "Zomboid" / "Server" / f"{server_name}.ini").read_text()
        assert FIXTURE_ID in configuration
        assert "PrintIngameTimeOneHour" in configuration

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["*** SERVER STARTED ***"],
            START_TIMEOUT,
        )

        if workshop_fixture:
            fresh_log = install_dir / "Zomboid" / "server-console.txt"
            assert_workshop_loaded(fresh_log.read_text(encoding="utf-8", errors="replace"))

        # status
        run_and_assert_ok(env, server_name, "status")

        wait_for_info_protocol(env, server_name, "udp", 300)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert any(
            marker in query_result.stdout
            for marker in ("Server is responding", "Server port is open")
        ), (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert any(
            marker in info_result.stdout
            for marker in ("Players     : 0/", "Server port is open")
        ), (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT
        )

    assert_alphagsm_result_ok(stop_result)

    # verify stopped
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "remove", "workshop", FIXTURE_ID)
        run_and_assert_ok(env, server_name, "mod", "apply")
        configuration = (install_dir / "Zomboid" / "Server" / f"{server_name}.ini").read_text()
        assert "WorkshopItems=\n" in configuration
        assert "Mods=\n" in configuration


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for public Workshop load validation")
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
@pytest.mark.timeout(3600)
def test_projectzomboid_workshop_lifecycle(tmp_path, runtime_backend):
    test_projectzomboid_lifecycle(tmp_path, runtime_backend, workshop_fixture=True)
