"""Integration test for stationeersserver."""

import os
import json
from pathlib import Path
import sys

import pytest

from conftest import (
    default_runtime_backend,
    effective_runtime_backend,
    resolve_steamcmd_linux_runtime_image,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_log_marker,
    wait_for_generic_udp_closed,
)
from gamemodules.stationeersserver import steam_app_id
from tests.smoke_tests.stationeersserver_workshop import FIXTURE_ID, WORLD, assert_workshop_loaded

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _create_or_skip_disabled(env, server_name, module_name):
    result = run_alphagsm(env, server_name, "create", module_name)
    log_command_result("alphagsm " + " ".join((server_name, "create", module_name)), result)
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if "is currently disabled" in combined:
        pytest.skip(combined[:300].replace("\n", " | "))
    assert result.returncode == 0, result.stderr or result.stdout


def test_stationeersserver_lifecycle(tmp_path, runtime_backend=None, workshop_fixture=False):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    backend = effective_runtime_backend(runtime_backend, module_name="stationeersserver")
    module_name = "stationeersserver"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    reusable = os.environ.get("ALPHAGSM_STATIONEERSSERVER_TEST_INSTALL")
    if reusable:
        install_dir = Path(reusable).expanduser().resolve()
        assert install_dir.is_relative_to(Path(os.environ["ALPHAGSM_WORK_DIR"]).resolve())
        assert (install_dir / "rocketstation_DedicatedServer.x86_64").is_file()
        (install_dir / "server.log").unlink(missing_ok=True)
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itstation" + tmp_path.name.replace("_", "")[-7:])[:15]

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
    _create_or_skip_disabled(env, server_name, module_name)
    if backend == "docker":
        run_and_assert_ok(env, server_name, "set", "image", resolve_steamcmd_linux_runtime_image())
    run_and_assert_ok(env, server_name, "set", "updateport", str(pick_free_tcp_port()))
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "set", "savename", server_name)
        run_and_assert_ok(env, server_name, "set", "worldname", WORLD)

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", FIXTURE_ID)
        run_and_assert_ok(env, server_name, "mod", "apply")

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = install_dir / "server.log"
        wait_for_log_marker(
            log_path,
            [
                "RakNet successfully hosted with Address",
                "registered with session #",
            ],
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )
        wait_for_info_protocol(env, server_name, "udp", START_TIMEOUT)
        if workshop_fixture:
            text = log_path.read_text(errors="replace")
            save = install_dir / "saves" / server_name / f"{server_name}.save"
            assert_workshop_loaded(text, save)
            evidence = Path(os.environ.get("ALPHAGSM_WORK_DIR", tmp_path)) / "evidence"
            evidence.mkdir(exist_ok=True)
            (evidence / f"stationeersserver-{backend}.log").write_text(text)

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "UDP ping on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "UDP ping on port" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, (
            f"Expected managed port in info JSON: {_info_data!r}"
        )
    finally:
        # stop
        stopped = capture_alphagsm_stop(env, server_name, sys.exc_info()[1], timeout=90)
    assert_alphagsm_result_ok(stopped)

    # verify stopped
    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)

    result = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in result.stdout
    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "cleanup")
        assert "alphagsm-" + FIXTURE_ID not in (install_dir / "modconfig.xml").read_text()


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for native public Workshop checks")
@pytest.mark.parametrize("runtime_backend", ["process", "docker"])
def test_stationeersserver_native_workshop(tmp_path, runtime_backend):
    test_stationeersserver_lifecycle(tmp_path, runtime_backend, workshop_fixture=True)
