"""Integration test for seserver."""

import json
import os
import re
from pathlib import Path
import sys

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    effective_runtime_backend,
    require_proton,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    wait_for_glob_log_marker,
    log_command_result,
    pick_free_udp_port,
    require_command,
    resolve_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    run_alphagsm,
    run_setup_with_port_retry,
    wait_for_generic_udp_closed,
    wait_for_info_protocol,
    write_config,
)
from gamemodules.seserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"
module_name = "seserver"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_seserver_lifecycle(tmp_path, runtime_backend=None, workshop_fixture=False):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = runtime_backend or os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    backend = effective_runtime_backend(runtime_backend, module_name=module_name)
    if backend == "docker":
        require_command("docker")
    else:
        require_proton()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    reusable = os.environ.get("ALPHAGSM_SESERVER_TEST_INSTALL")
    if reusable:
        install_dir = Path(reusable).expanduser().resolve()
        assert install_dir.is_relative_to(Path(os.environ["ALPHAGSM_WORK_DIR"]).resolve())
        assert (install_dir / "DedicatedServer64/SpaceEngineersDedicated.exe").is_file()
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itse" + re.sub(r"[^A-Za-z0-9]", "", tmp_path.name)[-10:]
    image = resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
        LOCAL_WINE_PROTON_IMAGE,
        PUBLISHED_WINE_PROTON_IMAGE,
    )

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()

    run_and_assert_ok(env, server_name, "create", module_name)
    if backend == "docker":
        run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "wineprefix", str(install_dir / ".alphagsm-wineprefix"))

    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Space Engineers setup failed unexpectedly for app {steam_app_id}: "
            f"{result.stdout}\n{result.stderr}"
        )

    if workshop_fixture:
        run_and_assert_ok(env, server_name, "mod", "add", "workshop", "1521905890")
        run_and_assert_ok(env, server_name, "mod", "apply")
    for previous_log in install_dir.glob("SpaceEngineersDedicated_*.log"):
        previous_log.unlink()  # Fresh/exclusive disposable install; keep captured failure evidence elsewhere.
    run_and_assert_ok(env, server_name, "start")

    try:
        evidence = wait_for_glob_log_marker(install_dir, "SpaceEngineersDedicated_*.log", ["Game ready"], START_TIMEOUT, env=env, server_name=server_name)
        if workshop_fixture:
            assert "Modular" in evidence or "1521905890" in evidence, "Engine did not load the native Workshop package"
        wait_for_info_protocol(env, server_name, "udp", START_TIMEOUT)

        run_and_assert_ok(env, server_name, "status")

        query_result = run_and_assert_ok(env, server_name, "query")
        assert "UDP ping on port" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert "No further details available." in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("port") == port, (
            f"Expected game port in info JSON: {info_data!r}"
        )
    finally:
        original_error = sys.exc_info()[1]
        stopped = capture_alphagsm_stop(env, server_name, original_error, timeout=90)
        if workshop_fixture:
            cleaned = run_alphagsm(env, server_name, "mod", "cleanup")
            log_command_result("alphagsm mod cleanup", cleaned)
            if original_error is None:
                assert_alphagsm_result_ok(cleaned)
    assert_alphagsm_result_ok(stopped)

    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)

    result = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in result.stdout


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for native public Workshop checks")
@pytest.mark.parametrize("runtime_backend", ["process", "docker"])
def test_seserver_native_workshop(tmp_path, runtime_backend):
    test_seserver_lifecycle(tmp_path, runtime_backend, workshop_fixture=True)
