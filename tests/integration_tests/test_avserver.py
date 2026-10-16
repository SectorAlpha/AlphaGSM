"""Integration test for avserver."""

import os
from pathlib import Path
import shutil
import sys

import pytest

from conftest import (
    workshop_runtime_backends,
    default_runtime_backend,
    effective_runtime_backend,
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
    wait_for_runtime_log_marker,
    wait_for_udp_closed,
    wait_for_info_protocol,
    resolve_steamcmd_linux_runtime_image,
)
from gamemodules.avserver import steam_app_id
from tests.smoke_tests.avserver_workshop import FIXTURE_ID, PROBE, assert_workshop_loaded

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


@pytest.mark.timeout(3600)
def test_avserver_lifecycle(tmp_path, runtime_backend=None, workshop_fixture=False):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "avserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itav" + tmp_path.name.replace("_", "")[-8:])[:15]

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()
    steam_query_port = port + 20

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    if effective_runtime_backend(runtime_backend, module_name=module_name) == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    cache = os.environ.get("ALPHAGSM_AVSERVER_TEST_CACHE")
    if cache:
        source = Path(cache).expanduser().resolve()
        assert (source / "bin/AvorionServer").is_file()
        shutil.copytree(source, install_dir, ignore=shutil.ignore_patterns("galaxies", ".alphagsm", "steamapps"))

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", FIXTURE_ID)
        run_and_assert_ok(env, server_name, "mod", "apply")

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        wait_for_runtime_log_marker(
            env,
            server_name,
            ["Server startup complete."],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")
        wait_for_info_protocol(env, server_name, "udp", 120)
        if workshop_fixture:
            run_and_assert_ok(env, server_name, "send", PROBE)
            evidence = wait_for_runtime_log_marker(env, server_name, ["ALPHAGSM_AZIMUTH_RESULT=42"], 90)
            assert_workshop_loaded(evidence)
            if os.environ.get("ALPHAGSM_WORK_DIR"):
                evidence_dir = Path(os.environ["ALPHAGSM_WORK_DIR"]) / "evidence"
                evidence_dir.mkdir(exist_ok=True)
                (evidence_dir / f"avserver-{runtime_backend}.log").write_text(evidence)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Server port is open" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"
        assert "No further details available." in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == steam_query_port, f"Unexpected info JSON: {_info_data!r}"
    finally:
        # stop
        stop_result = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=90)
    assert_alphagsm_result_ok(stop_result)

    # verify stopped
    wait_for_udp_closed("127.0.0.1", steam_query_port, STOP_TIMEOUT)
    final_status = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in final_status.stdout
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "cleanup")
        assert FIXTURE_ID not in (install_dir / "galaxies" / server_name / "modconfig.lua").read_text()


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for public Workshop load checks")
@pytest.mark.parametrize("runtime_backend", workshop_runtime_backends())
def test_avserver_native_workshop(tmp_path, runtime_backend):
    test_avserver_lifecycle(tmp_path, runtime_backend, workshop_fixture=True)
