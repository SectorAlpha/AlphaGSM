"""Integration test for returntomoriaserver."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

from conftest import (
    assert_alphagsm_result_ok,
    capture_alphagsm_stop,
    fail_readiness_timeout,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    default_runtime_backend,
    effective_runtime_backend,
    require_command,
    resolve_runtime_image,
    require_command_for_runtime,
    require_proton,
    pick_free_tcp_port,
    run_setup_with_port_retry,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_udp_closed,
)
from gamemodules.returntomoriaserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90
SETUP_TIMEOUT = 3600  # 60 min: large SteamCMD payload under shared CI load
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
LOCAL_WINE_PROTON_IMAGE = "alphagsm-wine-proton-runtime:local"
PUBLISHED_WINE_PROTON_IMAGE = "ghcr.io/sectoralpha/alphagsm-wine-proton-runtime:latest"
_SAFE_STATUS_DIAGNOSTIC_FIELDS = ("Status", "AdvertisedAddressAndPort")
_STATUS_JSON_RELATIVE_DIRECTORIES = (
    Path("Moria") / "Config",
    Path("Moria") / "Saved" / "Config",
)
_STATUS_JSON_FILENAMES = ("status.json", "Status.json")
_STATUS_JSON_RELATIVE_PATHS = tuple(
    directory / filename
    for directory in _STATUS_JSON_RELATIVE_DIRECTORIES
    for filename in _STATUS_JSON_FILENAMES
)


def status_json_candidates(install_dir):
    """Return current and legacy upstream Status.json locations."""

    return tuple(
        Path(install_dir) / relative for relative in _STATUS_JSON_RELATIVE_PATHS
    )


def _safe_status_diagnostics(payload):
    """Return only non-secret Status.json fields suitable for test output."""

    if not isinstance(payload, dict):
        return None
    return {
        field: payload[field]
        for field in _SAFE_STATUS_DIAGNOSTIC_FIELDS
        if field in payload
    }


def wait_for_status_json_running(
    env,
    server_name: str,
    status_json_paths,
    timeout_seconds: int,
):
    """Poll supported Status.json locations until one reports ``running``."""

    if isinstance(status_json_paths, (str, Path)):
        status_json_paths = (Path(status_json_paths),)
    else:
        status_json_paths = tuple(Path(path) for path in status_json_paths)
    deadline = time.time() + timeout_seconds
    last_safe_status = None
    while time.time() < deadline:
        for status_json_path in status_json_paths:
            if status_json_path.is_file():
                try:
                    safe_status = _safe_status_diagnostics(
                        json.loads(
                            status_json_path.read_text(encoding="utf-8-sig")
                        )
                    )
                except json.JSONDecodeError:
                    safe_status = None
                if safe_status is not None:
                    last_safe_status = safe_status
                    if safe_status.get("Status") == "running":
                        return safe_status
        time.sleep(5)
    try:
        fail_readiness_timeout(
            env,
            server_name,
            "Status.json did not report a running Return to Moria server within {}s. "
            "Last safe status fields: {!r}".format(
                timeout_seconds,
                last_safe_status,
            ),
        )
    finally:
        env = None
        last_safe_status = None


@pytest.mark.timeout(TEST_TIMEOUT)
def test_returntomoriaserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "returntomoriaserver"
    selected_runtime_backend = effective_runtime_backend(
        runtime_backend,
        module_name=module_name,
    )
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    image = None
    if selected_runtime_backend == "process":
        require_proton()
    else:
        require_command("docker")
        image = resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
        LOCAL_WINE_PROTON_IMAGE,
        PUBLISHED_WINE_PROTON_IMAGE,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itreturntomo"

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
    if image is not None:
        run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    result, port = run_setup_with_port_retry(
        env,
        server_name,
        port,
        install_dir,
        timeout=SETUP_TIMEOUT,
        steam_app_id=steam_app_id,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    try:
        # start
        run_and_assert_ok(env, server_name, "start")
        # The enabled upstream console can wait for a key before world load
        # completes and Status.json reaches its running state.
        run_and_assert_ok(env, server_name, "send", " ")

        # wait for readiness
        status_json_path = status_json_candidates(install_dir)
        status_payload = wait_for_status_json_running(
            env,
            server_name,
            status_json_path,
            START_TIMEOUT,
        )
        info_data = wait_for_info_protocol(
            env,
            server_name,
            "udp",
            START_TIMEOUT,
            expected_port=port,
        )
        ready_port = info_data.get("port")
        info_data = None
        assert ready_port == port, "Expected game-port UDP readiness on fresh server"

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        query_ready = "Server port is open" in query_result.stdout
        query_result = None
        assert query_ready, "Expected Return to Moria query readiness"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        info_ready = "No further details available." in info_result.stdout
        info_result = None
        assert info_ready, "Expected Return to Moria info readiness"

        # info --json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        info_protocol = _info_data.get("protocol")
        info_port = _info_data.get("port")
        _info_data = None
        info_json_result = None
        assert info_protocol == "udp", "Expected udp protocol in info JSON"
        assert info_port == port, "Expected managed game port in info JSON"
        advertised_address = status_payload.get("AdvertisedAddressAndPort", "")
        assert advertised_address.endswith(f":{port}"), (
            "Expected advertised port to match the managed game port: "
            f"{advertised_address!r}"
        )
    finally:
        # stop
        stop_result = capture_alphagsm_stop(
            env,
            server_name,
            sys.exc_info()[1],
        )

    # verify stopped
    assert_alphagsm_result_ok(stop_result)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
