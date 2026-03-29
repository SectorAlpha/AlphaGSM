"""Integration test for sevendaystodie."""

import glob
import time
from pathlib import Path

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_log_marker,
    wait_for_tcp_closed,
    wait_for_udp_closed,
)

pytestmark = pytest.mark.integration

START_TIMEOUT = 900  # 7DTD generates a game world on first start, which takes several minutes
STOP_TIMEOUT = 90


@pytest.mark.timeout(3600)  # 60 min: large download (~12 GB) + world generation on first start
def test_sevendaystodie_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itsevendaystod"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "sevendaystodie")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        # 7DTD writes all server output to output_log__DATE.txt in the install dir (not stdout).
        # Wait up to 60s for the output log file to appear, then use it for marker detection.
        actual_log_path = home_dir / "logs" / f"AlphaGSM-IT#{server_name}.log"  # fallback
        deadline_find = time.time() + 60
        while time.time() < deadline_find:
            candidates = sorted(glob.glob(str(install_dir / "output_log__*.txt")))
            if candidates:
                actual_log_path = Path(candidates[-1])
                break
            time.sleep(2)

        # wait for readiness
        wait_for_log_marker(
            actual_log_path,
            ["INF StartGame done", "StartGame done", "GameSense", "INF Net:"],
            START_TIMEOUT,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server is responding" in query_result.stdout
            or "Server port is open" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Players     : 0/" in info_result.stdout
            or "Server port is open" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] in ("a2s", "tcp"), (
            f"Unexpected protocol in info JSON: {_info_data!r}"
        )
        if _info_data["protocol"] == "a2s":
            assert _info_data.get("players") == 0, (
                f"Expected 0 players on fresh server: {_info_data!r}"
            )
    finally:
        # stop
        run_and_assert_ok(env, server_name, "stop")

    # verify stopped
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT)
