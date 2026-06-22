"""Integration test for sonsoftheforestserver."""

import json
import os

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    resolve_runtime_image,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_a2s_ready,
    wait_for_info_protocol,
    wait_for_log_marker,
    wait_for_udp_closed,
)
from gamemodules.sonsoftheforestserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: large SteamCMD payload under shared CI load
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "sonsoftheforestserver"
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_sonsoftheforestserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = ("itsotf" + tmp_path.name.replace("_", "")[-9:])[:15]
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
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "image", image)
    run_and_assert_ok(env, server_name, "set", "dir", str(install_dir))
    run_and_assert_ok(env, server_name, "set", "queryport", str(pick_free_tcp_port()))
    run_and_assert_ok(env, server_name, "set", "blobsyncport", str(pick_free_tcp_port()))

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    dedicated_config = install_dir / "user-data" / "dedicatedserver.cfg"
    assert dedicated_config.is_file(), f"Expected setup to create {dedicated_config}"
    config_data = json.loads(dedicated_config.read_text(encoding="utf-8"))
    query_port = int(config_data["QueryPort"])
    blob_sync_port = int(config_data["BlobSyncPort"])
    assert config_data["GamePort"] == port, config_data
    assert config_data["SkipNetworkAccessibilityTest"] is True, config_data

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # wait for readiness
        log_path = install_dir / "user-data" / "logs" / "sotf_log.txt"
        wait_for_log_marker(
            log_path,
            [
                "Dedicated server configuration",
                "GamePort",
                "QueryPort",
                "BlobSyncPort",
                "[Self-Tests]",
            ],
            START_TIMEOUT,
            env=env,
            server_name=server_name,
        )
        wait_for_a2s_ready("127.0.0.1", query_port, START_TIMEOUT, log_path=log_path)
        _info_data = wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)
        assert _info_data["port"] == query_port, (
            f"Expected Sons Of The Forest info port {query_port}: {_info_data!r}"
        )

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
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {_info_data!r}"
        )
        assert _info_data["port"] == query_port, (
            f"Expected query port {query_port} in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_udp_closed("127.0.0.1", query_port, STOP_TIMEOUT)
