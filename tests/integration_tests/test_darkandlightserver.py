"""Integration test for darkandlightserver."""

import json
import time
from pathlib import Path

import pytest

from conftest import (
    require_integration_opt_in,
    require_steamcmd_opt_in,
    require_command,
    require_proton,
    pick_free_tcp_port,
    write_config,
    alphagsm_env,
    run_and_assert_ok,
    run_alphagsm,
    log_command_result,
    skip_for_known_steamcmd_issue,
    wait_for_generic_udp_closed,
)
from gamemodules.darkandlightserver import steam_app_id

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 90


def _tail_if_exists(path, line_count=40):
    """Return the last *line_count* lines from *path* if it exists."""

    file_path = Path(path)
    if not file_path.is_file():
        return f"<missing: {file_path}>"
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return f"<empty: {file_path}>"
    return "\n".join(lines[-line_count:])


def _wait_for_udp_or_fail_fast(env, server_name, timeout_seconds, *, config_path, install_dir):
    """Wait for UDP readiness, but fail early if the screen session dies."""

    deadline = time.time() + timeout_seconds
    screen_log_path = config_path.parent / "home" / "logs" / f"AlphaGSM-IT#{server_name}.log"
    dnl_log_path = install_dir / "DNL" / "Saved" / "Logs" / "DNL.log"
    last_info_result = None

    while time.time() < deadline:
        info_result = run_alphagsm(env, server_name, "info", "--json")
        last_info_result = info_result
        info_ok = info_result.returncode == 0
        if info_ok:
            info_data = json.loads(info_result.stdout.strip())
            if info_data.get("protocol") == "udp":
                return info_data

        status_result = run_alphagsm(env, server_name, "status")
        if "Server isn't running as no screen session" in status_result.stdout:
            pytest.fail(
                "Dark and Light screen session died before UDP readiness.\n"
                f"status stdout:\n{status_result.stdout}\n"
                f"last info returncode: {info_result.returncode}\n"
                f"last info stderr:\n{info_result.stderr}\n"
                f"screen log tail ({screen_log_path}):\n{_tail_if_exists(screen_log_path)}\n"
                f"DNL log tail ({dnl_log_path}):\n{_tail_if_exists(dnl_log_path)}"
            )

        time.sleep(5)

    pytest.fail(
        "Dark and Light never reached UDP readiness before timeout.\n"
        f"last info returncode: {last_info_result.returncode if last_info_result else 'n/a'}\n"
        f"last info stdout:\n{last_info_result.stdout if last_info_result else ''}\n"
        f"last info stderr:\n{last_info_result.stderr if last_info_result else ''}\n"
        f"screen log tail ({screen_log_path}):\n{_tail_if_exists(screen_log_path)}\n"
        f"DNL log tail ({dnl_log_path}):\n{_tail_if_exists(dnl_log_path)}"
    )


def test_darkandlightserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    require_proton()
    require_command("screen")

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    install_dir = tmp_path / "server"
    config_path = tmp_path / "alphagsm.conf"
    server_name = "itdarkandlight"

    write_config(config_path, home_dir, session_tag="AlphaGSM-IT#")
    env = alphagsm_env(config_path)
    port = pick_free_tcp_port()

    # create
    run_and_assert_ok(env, server_name, "create", "darkandlightserver")

    # setup
    result = run_and_assert_ok(env, server_name, "setup", "-n", str(port), str(install_dir))
    if result.returncode != 0:
        skip_for_known_steamcmd_issue(result, app_id=steam_app_id)

    # start
    run_and_assert_ok(env, server_name, "start")

    try:
        _wait_for_udp_or_fail_fast(
            env,
            server_name,
            START_TIMEOUT,
            config_path=config_path,
            install_dir=install_dir,
        )

        # status
        run_and_assert_ok(env, server_name, "status")

        # query
        query_result = run_and_assert_ok(env, server_name, "query")
        assert (
            "Server port is open (UDP ping on port" in query_result.stdout
        ), f"Unexpected query output: {query_result.stdout!r}"

        # info
        info_result = run_and_assert_ok(env, server_name, "info")
        assert (
            "Server port is open (UDP ping on port" in info_result.stdout
        ), f"Unexpected info output: {info_result.stdout!r}"

        # info --json
        import json as _info_json
        info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = _info_json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "udp", (
            f"Expected udp protocol in info JSON: {_info_data!r}"
        )
        assert _info_data.get("port") == port, f"Unexpected info JSON: {_info_data!r}"
    finally:
        # stop
        log_command_result("alphagsm stop", run_alphagsm(env, server_name, "stop"))

    # verify stopped
    wait_for_generic_udp_closed("127.0.0.1", port, STOP_TIMEOUT)
