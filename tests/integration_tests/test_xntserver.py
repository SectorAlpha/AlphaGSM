"""Integration test for xntserver."""

import os
import re
import subprocess
import time
import pytest

from conftest import (
    require_integration_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 600
STOP_TIMEOUT = 90
LOCAL_DOCKER_IMAGE = "alphagsm-quake-linux-runtime:local"
PUBLISHED_DOCKER_IMAGE = "ghcr.io/sectoralpha/alphagsm-quake-linux-runtime:latest"


def resolve_quake_linux_runtime_image():
    """Prefer a branch-local Quake runtime image when available."""

    configured_image = os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_QUAKE_LINUX")
    if configured_image:
        return configured_image

    local_image = subprocess.run(
        ["docker", "image", "inspect", LOCAL_DOCKER_IMAGE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if local_image.returncode == 0:
        return LOCAL_DOCKER_IMAGE

    return PUBLISHED_DOCKER_IMAGE


def _run_setup_with_port_retry(env, server_name, install_dir, initial_port):
    """Retry setup once when CI loses the selected port to another listener."""

    port = initial_port
    for attempt in range(2):
        result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
        log_command_result(
            f"alphagsm {server_name} setup -n {port} {install_dir}",
            result,
        )
        if result.returncode == 0:
            return port
        combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
        match = re.search(r"Recommended free port set: port=(\d+)", combined)
        if attempt == 0 and match is not None:
            port = int(match.group(1))
            continue
        skip_for_known_steamcmd_issue(result)
        assert result.returncode == 0, result.stderr or result.stdout
    return port


def test_xntserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itxntserver"
    image = resolve_quake_linux_runtime_image()

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        backend="subprocess",
        runtime_backend="auto",
        module_name="xntserver",
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "xntserver")
    run_and_assert_ok(env, server_name, "set", "image", image)

    # setup
    port = _run_setup_with_port_retry(env, server_name, install_dir, port)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # status
        run_and_assert_ok(env, server_name, "status")

        # Xonotic uses the Quake UDP getstatus protocol, not A2S.
        wait_for_info_protocol(env, server_name, "quake", START_TIMEOUT)

        # Give the server additional time to stabilise — it can respond to one
        # Quake probe then crash if a runtime library loads lazily and fails.
        # Recheck through AlphaGSM after the DarkPlaces rate-limit window.
        time.sleep(15)
        wait_for_info_protocol(env, server_name, "quake", START_TIMEOUT)

        # DarkPlaces (Xonotic's engine) rate-limits getstatus responses by
        # source IP.  Wait long enough for the rate-limit window to expire
        # before running `alphagsm query` so that request is not silently
        # dropped by the server.
        time.sleep(15)

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # `alphagsm info` sends its own getstatus probe; the DarkPlaces
        # rate-limit applies per-source-IP so we must wait again.
        time.sleep(15)

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players    : 0/" in info_result.stdout  # Quake status format (4 spaces)
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        # `alphagsm info --json` also sends its own getstatus probe; the
        # DarkPlaces rate-limit applies per-source-IP so we must wait again.
        time.sleep(15)

        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "quake", (
            f"Expected quake protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {_info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
    wait_for_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
