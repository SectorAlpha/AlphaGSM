import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"
TEST_TIMEOUT_SECONDS = 1200


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _write_config(config_path, home_dir):
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


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run_alphagsm(env, *args, timeout=TEST_TIMEOUT_SECONDS):
    command = [sys.executable, str(ALPHAGSM_SCRIPT)] + list(args)
    return subprocess.run(
        command,
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


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


def _load_server_data(home_dir, server_name):
    return json.loads((home_dir / "conf" / f"{server_name}.json").read_text())


def test_etlegacy_downloads_latest_release_and_installs(tmp_path):
    _require_integration_opt_in()

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "etlegacy-server"
    config_path = tmp_path / "alphagsm-etlegacy.conf"
    server_name = "itetlegacy"

    home_dir.mkdir()
    _write_config(config_path, home_dir)
    env = _alphagsm_env(config_path)

    _run_and_assert_ok(env, server_name, "create", "etlegacyserver")
    _run_and_assert_ok(env, server_name, "setup", "--noask", "27960", str(install_dir))

    data = _load_server_data(home_dir, server_name)
    assert data["url"]
    assert data["version"]
    assert data["download_name"]
    assert data["exe_name"] == "etl.x86_64"
    assert (install_dir / "etl.x86_64").exists()

    # A second setup pass should reuse the resolved settings cleanly.
    _run_and_assert_ok(env, server_name, "setup", "--noask", "27960", str(install_dir))


def test_cod2_downloads_default_archive_and_installs(tmp_path):
    _require_integration_opt_in()

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "cod2-server"
    config_path = tmp_path / "alphagsm-cod2.conf"
    server_name = "itcod2"

    home_dir.mkdir()
    _write_config(config_path, home_dir)
    env = _alphagsm_env(config_path)

    _run_and_assert_ok(env, server_name, "create", "cod2server")
    _run_and_assert_ok(env, server_name, "setup", "--noask", "28960", str(install_dir))

    data = _load_server_data(home_dir, server_name)
    assert "cod2-lnxded" in data["url"]
    assert data["download_name"] == "cod2-lnxded-1.3-06232006.tar.bz2"
    assert data["exe_name"] == "cod2_lnxded"
    assert (install_dir / "cod2_lnxded").exists()
