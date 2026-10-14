"""Integration test for wreckfestserver."""

import json
import os
from pathlib import Path
import shutil
import sys

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    effective_runtime_backend,
    require_command_for_runtime,
    require_proton,
    capture_alphagsm_stop,
    assert_alphagsm_result_ok,
    log_command_result,
    pick_free_udp_port,
    require_command,
    resolve_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_alphagsm,
    run_and_assert_ok,
    run_setup_with_port_retry,
    wait_for_info_protocol,
    wait_for_log_marker,
    wait_for_generic_udp_closed,
    wait_for_tcp_closed,
    write_config,
)
from gamemodules.wreckfestserver import steam_app_id
from tests.smoke_tests.wreckfestserver_workshop import FIXTURE_ID, TRACK, wait_for_workshop_loaded
from tests.smoke_tests.wreckfestserver_diagnostics import collect_remote_diagnostics

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 900
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_wreckfestserver_lifecycle(tmp_path):
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    _run_wreckfestserver_lifecycle(tmp_path, runtime_backend=runtime_backend)


def _cleanup_wreckfest(env, server_name, workshop_fixture, original_error):
    """Stop even failed launches and clean managed content only after a successful stop."""
    stopped = capture_alphagsm_stop(env, server_name, original_error, timeout=STOP_TIMEOUT)
    if stopped is not None and stopped.returncode == 0 and workshop_fixture:
        try:
            cleaned = run_alphagsm(env, server_name, "mod", "cleanup")
            log_command_result("alphagsm mod cleanup", cleaned)
            if original_error is None:
                assert_alphagsm_result_ok(cleaned)
        except Exception as error:
            if original_error is None:
                raise
            print(f"[diagnostic] Workshop cleanup raised {type(error).__name__}; preserving lifecycle failure")
    if original_error is None:
        assert_alphagsm_result_ok(stopped)


def _diagnose_wreckfest(env, server_name, queryport, install_dir, backend, quick=False, gameport=None):
    """Observe the still-running failed server without replacing its failure."""
    try:
        container = None
        if backend == "docker":
            doctor = run_alphagsm(env, server_name, "doctor", "--json", timeout=15,
                                  capture_diagnostics=False)
            if doctor.returncode == 0:
                container = json.loads(doctor.stdout).get("runtime", {}).get("container_name")
        collect_remote_diagnostics(queryport, install_dir, container, quick=quick, gameport=gameport)
    except Exception as error:
        print(f"[diagnostic] Wreckfest observation failed: {type(error).__name__}: {error}")


def _run_wreckfestserver_lifecycle(tmp_path, *, runtime_backend, workshop_fixture=False):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    backend = effective_runtime_backend(runtime_backend, module_name="wreckfestserver")
    if backend == "docker":
        require_command("docker")
    else:
        require_command_for_runtime("xvfb-run", runtime_backend=runtime_backend, module_name="wreckfestserver")
        require_proton()

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    reusable_install = os.environ.get("ALPHAGSM_WRECKFESTSERVER_TEST_INSTALL")
    if reusable_install:
        work_root = Path(os.environ["ALPHAGSM_WORK_DIR"]).resolve()
        install_dir = Path(reusable_install).expanduser().resolve()
        assert install_dir.is_relative_to(work_root), "Reusable test install must be owned by this work root"
        assert (install_dir / "Wreckfest_x64.exe").is_file()
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itwreck" + tmp_path.name.replace("_", "")[-8:])[:15]

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend=runtime_backend,
        module_name="wreckfestserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_udp_port()
    queryport = pick_free_udp_port()
    while queryport == port:
        queryport = pick_free_udp_port()
    steamport = pick_free_udp_port()
    while steamport in {port, queryport}:
        steamport = pick_free_udp_port()
    run_and_assert_ok(env, server_name, "create", "wreckfestserver")
    if backend == "docker":
        image = resolve_runtime_image(
            "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
            LOCAL_WINE_PROTON_IMAGE,
            PUBLISHED_WINE_PROTON_IMAGE,
        )
        run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "wineprefix", str(install_dir / ".alphagsm-wineprefix"))
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))
    run_and_assert_ok(env, server_name, "set", "steamport", str(steamport))
    run_and_assert_ok(env, server_name, "set", "servername", "AlphaGSM Wreckfest IT")
    run_and_assert_ok(env, server_name, "set", "maxplayers", "16")
    cache = os.environ.get("ALPHAGSM_WRECKFESTSERVER_TEST_CACHE")
    if cache and not reusable_install:
        source = Path(cache).expanduser().resolve()
        assert (source / "Wreckfest_x64.exe").is_file()
        shutil.copytree(source, install_dir, ignore=shutil.ignore_patterns(
            ".alphagsm", ".alphagsm-wineprefix", "mods", "server_config.cfg", "log.txt"))

    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        pytest.fail(
            f"Wreckfest setup failed unexpectedly for app {steam_app_id}: "
            f"{result.stdout}\n{result.stderr}"
        )

    try:
        if workshop_fixture:
            run_and_assert_ok(env, server_name, "mod", "add", "workshop", FIXTURE_ID)
            run_and_assert_ok(env, server_name, "mod", "apply")
            run_and_assert_ok(env, server_name, "set", "track", TRACK)
        # This install is disposable and stopped; only its native log is rotated.
        native_log = install_dir / "log.txt"
        assert not native_log.is_symlink(), "Native test log must not be a symlink"
        assert native_log.resolve().parent == install_dir.resolve()
        native_log.unlink(missing_ok=True)
        run_and_assert_ok(env, server_name, "start")
        wait_for_log_marker(native_log, ["Server connected."], START_TIMEOUT,
                            env=env, server_name=server_name)
        # TCP proves connectivity only; the fresh engine log establishes startup.
        wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT, expected_port=port)

        status = run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status.stdout
        if workshop_fixture:
            run_and_assert_ok(env, server_name, "send", "tracks")
            evidence = wait_for_workshop_loaded(
                lambda remaining: run_and_assert_ok(
                    env, server_name, "logs", "-n", "2000", timeout=min(15, remaining)).stdout,
                timeout_seconds=90,
            )
            if os.environ.get("ALPHAGSM_WORK_DIR"):
                target = Path(os.environ["ALPHAGSM_WORK_DIR"]) / "evidence"
                target.mkdir(exist_ok=True)
                (target / f"wreckfestserver-{backend}.log").write_text(evidence)

        query_result = run_and_assert_ok(env, server_name, "query")
        assert f"TCP ping on port {port}" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        info_result = run_and_assert_ok(env, server_name, "info")
        assert f"TCP ping on port {port}" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )
        assert "No further details available." in info_result.stdout

        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        info_data = json.loads(info_json_result.stdout.strip())
        assert info_data["protocol"] == "tcp", (
            f"Expected explicit TCP connectivity in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, (
            f"Expected reported info port {port}: {info_data!r}"
        )
        assert set(info_data) == {"protocol", "port", "latency_ms"}, info_data
        assert isinstance(info_data["latency_ms"], (int, float)) and info_data["latency_ms"] >= 0
    except BaseException:
        _diagnose_wreckfest(env, server_name, queryport, install_dir, backend, gameport=port)
        raise
    finally:
        _cleanup_wreckfest(env, server_name, workshop_fixture, sys.exc_info()[1])

    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
    for claimed_port in (port, queryport, steamport):
        wait_for_generic_udp_closed("127.0.0.1", claimed_port, STOP_TIMEOUT)
    status = run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in status.stdout
    if workshop_fixture:
        assert "alphagsm-" + FIXTURE_ID not in (install_dir / "server_config.cfg").read_text()


@pytest.mark.skipif(os.environ.get("ALPHAGSM_RUN_WORKSHOP") != "1",
                    reason="Set ALPHAGSM_RUN_WORKSHOP=1 for native public Workshop checks")
@pytest.mark.parametrize("runtime_backend", ["process", "docker"])
def test_wreckfestserver_native_workshop(tmp_path, runtime_backend):
    _run_wreckfestserver_lifecycle(tmp_path, runtime_backend=runtime_backend, workshop_fixture=True)
