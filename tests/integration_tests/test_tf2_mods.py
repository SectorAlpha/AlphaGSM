"""Integration coverage for TF2 curated mod commands."""

import contextlib
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import socketserver
import subprocess
import sys
import tarfile
import threading

import pytest

from conftest import write_config
from gamemodules.teamfortress2 import steam_app_id
import gamemodules.teamfortress2 as tf2
import gamemodules.teamfortress2.mods as tf2_mods

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
ALPHAGSM_SCRIPT = REPO_ROOT / "alphagsm"


def _require_integration_opt_in():
    if os.environ.get("ALPHAGSM_RUN_INTEGRATION") != "1":
        pytest.skip("Set ALPHAGSM_RUN_INTEGRATION=1 to run integration tests")


def _require_steamcmd_opt_in():
    if os.environ.get("ALPHAGSM_RUN_STEAMCMD") != "1":
        pytest.skip("Set ALPHAGSM_RUN_STEAMCMD=1 to run SteamCMD integration tests")


def _require_network_opt_in():
    if os.environ.get("ALPHAGSM_RUN_NETWORK") != "1":
        pytest.skip("Set ALPHAGSM_RUN_NETWORK=1 to run tests that hit the real network")


def _require_command(name):
    if shutil.which(name) is None:
        pytest.skip(f"Required command not available: {name}")


def _pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _alphagsm_env(config_path):
    env = os.environ.copy()
    env["ALPHAGSM_CONFIG_LOCATION"] = str(config_path)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run_alphagsm(env, *args, timeout=1200):
    return subprocess.run(
        [sys.executable, str(ALPHAGSM_SCRIPT), *args],
        env=env,
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _run_and_assert_ok(env, *args, timeout=1200):
    result = _run_alphagsm(env, *args, timeout=timeout)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def _skip_for_known_tf2_setup_issue(result):
    combined = "\n".join(part for part in (result.stdout, result.stderr) if part)
    known_markers = (
        "tf/cfg/server.cfg",
        "No such file or directory",
        f"Failed to install app '{steam_app_id}' (Missing configuration)",
    )
    if all(marker in combined for marker in known_markers):
        pytest.skip("TF2 setup still hits the known missing-configuration SteamCMD issue")


def _build_curated_archive(tmp_path):
    archive_root = tmp_path / "archive-root"
    payload = archive_root / "addons" / "sourcemod" / "plugins"
    payload.mkdir(parents=True)
    (payload / "base.smx").write_text("plugin", encoding="utf-8")
    archive_path = tmp_path / "sourcemod.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(archive_root / "addons", arcname="addons")
    return archive_path


@contextlib.contextmanager
def _serve_directory(root: Path):
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format, *args):
            return

    with socketserver.TCPServer(("127.0.0.1", 0), QuietHandler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{httpd.server_address[1]}"
        finally:
            httpd.shutdown()
            thread.join()


def test_tf2_curated_mod_cli_flow(tmp_path):
    _require_integration_opt_in()
    _require_steamcmd_opt_in()
    _require_command("screen")

    home_dir = tmp_path / "alphagsm-home"
    install_dir = tmp_path / "tf2-server"
    config_path = tmp_path / "alphagsm-tf2.conf"
    server_name = "ittf2mods"
    port = _pick_free_port()

    home_dir.mkdir()
    write_config(config_path, home_dir, session_tag="AlphaGSM-TF2-MODS#")
    _build_curated_archive(tmp_path)

    with _serve_directory(tmp_path) as base_url:
        registry_path = tmp_path / "curated_mods.json"
        registry_path.write_text(
            json.dumps(
                {
                    "families": {
                        "sourcemod": {
                            "default": "stable",
                            "releases": {
                                "stable": {
                                    "url": f"{base_url}/sourcemod.tar.gz",
                                    "hosts": ["127.0.0.1"],
                                    "archive_type": "tar.gz",
                                    "destinations": ["addons"],
                                }
                            },
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        env = _alphagsm_env(config_path)
        env["ALPHAGSM_TF2_CURATED_REGISTRY_PATH"] = str(registry_path)

        _run_and_assert_ok(env, server_name, "create", "teamfortress2")
        setup_result = _run_alphagsm(
            env,
            server_name,
            "setup",
            "-n",
            str(port),
            str(install_dir),
            timeout=1200,
        )
        _skip_for_known_tf2_setup_issue(setup_result)
        assert setup_result.returncode == 0, setup_result.stderr or setup_result.stdout

        _run_and_assert_ok(env, server_name, "mod", "add", "curated", "sourcemod")
        _run_and_assert_ok(env, server_name, "mod", "apply")

        installed_file = install_dir / "tf" / "addons" / "sourcemod" / "plugins" / "base.smx"
        assert installed_file.exists()

        dump_result = _run_and_assert_ok(env, server_name, "dump")
        assert "sourcemod.stable" in dump_result.stdout


class _FakeData(dict):
    """Minimal in-memory datastore used by network integration tests."""

    def save(self):
        pass


class _FakeServer:
    """Minimal server double for calling TF2 module functions directly."""

    def __init__(self, install_dir: Path):
        self.name = "net-sm-test"
        self.data = _FakeData({"dir": str(install_dir) + "/"})


def test_curated_sourcemod_live_download_and_install(tmp_path):
    """Download and install SourceMod from the real sourcemod.net registry.

    Guards:
      ALPHAGSM_RUN_INTEGRATION=1  — general integration gate
      ALPHAGSM_RUN_NETWORK=1      — explicitly opts in to live network I/O

    This test does NOT require SteamCMD; it only installs mod files into a
    temporary directory, not a full TF2 game server.
    """
    _require_integration_opt_in()
    _require_network_opt_in()

    install_dir = tmp_path / "tf2-server"
    (install_dir / "tf").mkdir(parents=True)

    server = _FakeServer(install_dir)
    tf2.configure(server, ask=False, port=27015, dir=str(install_dir))
    tf2.command_functions["mod"](server, "add", "curated", "sourcemod")
    tf2.command_functions["mod"](server, "apply")

    mods = server.data["mods"]
    assert mods["last_apply"] == "success", f"apply failed — errors: {mods.get('errors')}"
    assert mods["errors"] == []
    assert any("sourcemod" in e["resolved_id"] for e in mods["installed"])

    # SourceMod always places at least its plugins directory.
    addons_dir = install_dir / "tf" / "addons" / "sourcemod"
    assert addons_dir.exists(), f"tf/addons/sourcemod not found under {install_dir}"

