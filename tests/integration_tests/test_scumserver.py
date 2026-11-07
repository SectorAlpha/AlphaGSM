"""Integration test for scumserver."""

import os

import pytest

from conftest import (
    alphagsm_env,
    default_runtime_backend,
    log_command_result,
    pick_free_tcp_port,
    require_command,
    resolve_runtime_image,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    run_and_assert_ok,
    run_alphagsm,
    run_setup_with_port_retry,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
    wait_for_tcp_closed,
    write_config,
)
from gamemodules.scumserver import steam_app_id

pytestmark = [pytest.mark.integration]
SETUP_TIMEOUT = 3600
START_TIMEOUT = 1800
STOP_TIMEOUT = 90
TEST_TIMEOUT = SETUP_TIMEOUT + START_TIMEOUT + 600
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "scumserver"


@pytest.mark.timeout(TEST_TIMEOUT)
def test_scumserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("docker")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itscumserver"
    image = resolve_runtime_image(
        "ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON",
        "alphagsm-wine-proton-runtime:local",
        "alphagsm-wine-proton-runtime:local",
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

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        info_data = wait_for_info_protocol(env, server_name, "tcp", START_TIMEOUT)

        # status
        run_and_assert_ok(env, server_name, "status")

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

        # info --json
        assert info_data["protocol"] == "tcp", (
            f"Expected tcp protocol in info JSON: {info_data!r}"
        )
        assert info_data["port"] == port, (
            f"Expected main game port in info JSON: {info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
