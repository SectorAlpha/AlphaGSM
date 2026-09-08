import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from conftest import (
    alphagsm_env,
    assert_alphagsm_result_ok,
    capture_alphagsm_stop,
    default_runtime_backend,
    effective_runtime_backend,
    pick_free_tcp_port,
    require_command_for_runtime,
    run_alphagsm,
    wait_for_info_protocol,
    wait_for_tcp_closed,
)


pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
STATUS_HELPER = REPO_ROOT / "tests" / "smoke_tests" / "minecraft_status.py"

TEST_TIMEOUT_SECONDS = 600
START_TIMEOUT_SECONDS = 180
STOP_TIMEOUT_SECONDS = 90


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _write_config(
    config_path,
    home_dir,
    *,
    runtime_backend="process",
    module_name=None,
    servermodulespackage="gamemodules.",
    backend="screen",
    docker_backend="subprocess",
):
    selected_runtime_backend = effective_runtime_backend(
        runtime_backend,
        module_name=module_name,
        servermodulespackage=servermodulespackage,
    )
    config_path.write_text(
        "\n".join(
            [
                "[core]",
                f"alphagsm_path = {home_dir}",
                f"userconf = {home_dir}",
                "",
                "[downloader]",
                f"db_path = {home_dir / 'downloads' / 'downloads.txt'}",
                f"target_path = {home_dir / 'downloads' / 'downloads'}",
                "",
                "[server]",
                f"datapath = {home_dir / 'conf'}",
                f"servermodulespackage = {servermodulespackage}",
                "",
                "[runtime]",
                f"backend = {selected_runtime_backend}",
                "",
                "[process]",
                f"backend = {backend}",
                "",
                "[docker]",
                f"backend = {docker_backend}",
                "",
                "[screen]",
                f"screenlog_path = {home_dir / 'logs'}",
                "sessiontag = AlphaGSM-IT#",
                "keeplogs = 1",
                "",
            ]
        )
        + "\n"
    )


def _write_java_wrapper(wrapper_path):
    wrapper_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'exec java -Xms256M -Xmx768M "$@"',
                "",
            ]
        )
    )
    wrapper_path.chmod(0o755)


def _fetch_latest_release_server_url():
    output = subprocess.check_output(
        [sys.executable, str(STATUS_HELPER), "latest-release"],
        timeout=30,
    )
    release_id, server_url = output.strip().split(b"\t")
    return release_id.decode(), server_url.decode()


def _alphagsm_env(config_path):
    return alphagsm_env(config_path)


def _run_alphagsm(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    return run_alphagsm(env, *args, timeout=timeout)


def _log_command_result(name, result):
    print(f"\n=== {name} ===")
    print(f"returncode: {result.returncode}")
    if result.stdout:
        print("stdout:")
        print(result.stdout.rstrip())
    if result.stderr:
        print("stderr:")
        print(result.stderr.rstrip())


def _run_and_assert_ok(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    result = _run_alphagsm(env, *args, timeout=timeout)
    _log_command_result("alphagsm " + " ".join(args), result)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _run_setup_with_download_retry(env, *args, timeout=TEST_TIMEOUT_SECONDS, attempts=3):
    last_result = None
    for attempt in range(1, attempts + 1):
        result = _run_alphagsm(env, *args, timeout=timeout)
        _log_command_result("alphagsm " + " ".join(args), result)
        if result.returncode == 0:
            return result
        combined = (result.stdout or "") + "\n" + (result.stderr or "")
        is_transient_download_failure = (
            "Network is unreachable" in combined
            or "can't download requested version" in combined
        )
        last_result = result
        if not is_transient_download_failure or attempt == attempts:
            break
        time.sleep(5)
    assert last_result is not None
    assert last_result.returncode == 0, last_result.stderr or last_result.stdout


def test_minecraft_vanilla_download_install_and_start(tmp_path):
    _require_integration_opt_in()
    runtime_backend = os.environ.get(
        "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
    )
    module_name = "minecraft.vanilla"
    _require_command("java")
    require_command_for_runtime(
        "screen",
        runtime_backend=runtime_backend,
        module_name=module_name,
    )

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "minecraft-server"
    config_path = tmp_path / "alphagsm-integration.conf"
    wrapper_path = tmp_path / "java-wrapper.sh"
    server_name = "itmc"
    port = pick_free_tcp_port()

    home_dir.mkdir()
    _write_config(
        config_path,
        home_dir,
        runtime_backend=runtime_backend,
        module_name=module_name,
    )
    _write_java_wrapper(wrapper_path)
    release_id, server_url = _fetch_latest_release_server_url()
    env = _alphagsm_env(config_path)

    _run_and_assert_ok(env, server_name, "create", module_name)
    _run_and_assert_ok(env, server_name, "set", "javapath", str(wrapper_path))
    _run_setup_with_download_retry(
        env,
        server_name,
        "setup",
        "-n",
        "-l",
        str(port),
        str(install_dir),
        "-u",
        server_url,
        timeout=TEST_TIMEOUT_SECONDS,
    )

    jar_path = install_dir / "minecraft_server.jar"
    assert jar_path.exists(), f"Expected downloaded jar at {jar_path}"
    assert (install_dir / "eula.txt").exists()
    assert (install_dir / "server.properties").exists()

    _run_and_assert_ok(env, server_name, "start", timeout=60)

    try:
        status = wait_for_info_protocol(
            env, server_name, "slp", START_TIMEOUT_SECONDS, expected_port=port
        )
        assert status["version"]
        assert release_id.split(".")[0] in status["version"]
        status_cmd = _run_and_assert_ok(env, server_name, "status")
        assert "Server is running" in status_cmd.stdout

        _run_and_assert_ok(env, server_name, "message", "hello world")

        # query — Minecraft doesn't implement A2S; expects TCP ping fallback
        query_result = _run_and_assert_ok(env, server_name, "query")
        print("\n=== query ===")
        print(query_result.stdout.strip())
        assert "Server port is open" in query_result.stdout, (
            f"Unexpected query output: {query_result.stdout!r}"
        )

        # info — Minecraft uses SLP; expects player count and description
        info_result = _run_and_assert_ok(env, server_name, "info")
        print("\n=== info ===")
        print(info_result.stdout.strip())
        assert "Server info (SLP" in info_result.stdout, (
            f"Unexpected info output: {info_result.stdout!r}"
        )
        assert "Players     : 0/20" in info_result.stdout, (
            f"Expected 0/20 player count (Minecraft default) in info output: {info_result.stdout!r}"
        )

        # info --json — verify structured JSON matches known Minecraft SLP values
        info_json_result = _run_and_assert_ok(env, server_name, "info", "--json")
        _info_data = json.loads(info_json_result.stdout.strip())
        assert _info_data["protocol"] == "slp", (
            f"Expected SLP protocol for Minecraft: {_info_data!r}"
        )
        assert _info_data.get("players_online") == 0, (
            f"Expected 0 players on fresh Minecraft server: {_info_data!r}"
        )
        assert _info_data.get("players_max") == 20, (
            f"Expected max-players=20 (Minecraft vanilla default): {_info_data!r}"
        )
    finally:
        stop_result = capture_alphagsm_stop(
            env, server_name, sys.exc_info()[1], timeout=STOP_TIMEOUT_SECONDS
        )

    assert_alphagsm_result_ok(stop_result)
    wait_for_tcp_closed("127.0.0.1", port, STOP_TIMEOUT_SECONDS)
    final_status = _run_and_assert_ok(env, server_name, "status")
    assert "isn't running" in final_status.stdout
