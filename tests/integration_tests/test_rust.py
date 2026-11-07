"""Integration test for rust."""

import os

import pytest

from conftest import (
    default_runtime_backend,
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command_for_runtime,
    pick_free_tcp_port_group,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_info_protocol,
)
from gamemodules.rust import steam_app_id

pytestmark = pytest.mark.integration

START_TIMEOUT = 1800  # Rust generates a new world on first start; CI runners (2 CPU / 7 GB) can take up to 25 min


@pytest.mark.timeout(4800)  # 80 min: download (~2 GB) + world generation on first start on slow CI runners
def test_rust_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend())
    module_name = "rust"
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itrust"

    write_config(
        config_path,
        home_dir,
        session_tag="AlphaGSM-IT#",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port_group(3)
    rconport = port + 1
    queryport = port + 2

    # create
    run_and_assert_ok(env, server_name, "create", module_name)
    run_and_assert_ok(env, server_name, "set", "rconport", str(rconport))
    run_and_assert_ok(env, server_name, "set", "queryport", str(queryport))

    # setup
    result = run_alphagsm(env, server_name, "setup", "-n", str(port), str(install_dir))
    log_command_result(
        f"alphagsm {server_name} setup -n {port} {install_dir}",
        result,
    )
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)
    assert result.returncode == 0, result.stderr or result.stdout

    # Use a small world so generation completes quickly in CI (default 3000 can OOM or
    # exceed the 900s START_TIMEOUT on GitHub-hosted 2-CPU / 7-GB runners).
    run_and_assert_ok(env, server_name, "set", "worldsize", "1000")

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # AlphaGSM resolves the correct host and port for both runtime backends.
        info_data = wait_for_info_protocol(env, server_name, "a2s", START_TIMEOUT)

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
        assert info_data["protocol"] == "a2s", (
            f"Expected a2s protocol in info JSON: {info_data!r}"
        )
        assert info_data.get("players") == 0, (
            f"Expected 0 players on fresh server: {info_data!r}"
        )
        assert info_data["port"] == queryport, (
            f"Expected reported query port {queryport}: {info_data!r}"
        )
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    status_result = run_and_assert_ok(env, server_name, "status")
    assert "Server isn't running as" in status_result.stdout
