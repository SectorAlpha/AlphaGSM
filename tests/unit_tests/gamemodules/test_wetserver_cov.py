"""Focused coverage tests for wetserver."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.modules.pop("gamemodules.wetserver", None)
with patch.dict(
    "sys.modules",
    {
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
    },
):
    import gamemodules.wetserver as mod
    from server import ServerError


class DummyData(dict):
    def save(self):
        pass

    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]

    def get(self, key, default=None):
        return super().get(key, default)


class DummyServer:
    def __init__(self, name="wettest"):
        self.name = name
        self.data = DummyData()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27961, dir=str(tmp_path))
    assert server.data["port"] == 27961
    assert server.data["url"] == mod.WET_DOWNLOAD_URL
    assert server.data["download_name"] == mod.WET_DOWNLOAD_NAME
    assert server.data["exe_name"] == "bin/Linux/x86/etded.x86"
    assert server.data["fs_game"] == "etmain"


def test_install_extracts_official_payload(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "url": mod.WET_DOWNLOAD_URL,
            "download_name": mod.WET_DOWNLOAD_NAME,
            "exe_name": "bin/Linux/x86/etded.x86",
            "hostname": "AlphaGSM wet",
            "port": 27960,
            "fs_game": "etmain",
            "configfile": "server.cfg",
        }
    )

    download_dir = tmp_path / "download-cache"
    download_dir.mkdir()
    installer = download_dir / mod.WET_INSTALLER_NAME
    installer.write_text("fake-installer", encoding="utf-8")

    def fake_run(cmd, check, stdout, stderr):
        target_dir = cmd[cmd.index("--target") + 1]
        os.makedirs(os.path.join(target_dir, "bin", "Linux", "x86"), exist_ok=True)
        os.makedirs(os.path.join(target_dir, "etmain"), exist_ok=True)
        with open(os.path.join(target_dir, "bin", "Linux", "x86", "etded.x86"), "w", encoding="utf-8") as handle:
            handle.write("binary")
        with open(os.path.join(target_dir, "etmain", "server.cfg"), "w", encoding="utf-8") as handle:
            handle.write('set sv_hostname "ETHost"\n')

    with patch.object(mod.downloader, "getpath", return_value=str(download_dir)), patch.object(
        mod.sp, "run", side_effect=fake_run
    ):
        mod.install(server)

    assert (tmp_path / "bin" / "Linux" / "x86" / "etded.x86").is_file()
    assert server.data["current_url"] == mod.WET_DOWNLOAD_URL


def test_sync_server_config_updates_stock_server_cfg(tmp_path):
    server = DummyServer("wetcfg")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "fs_game": "etmain",
            "configfile": "server.cfg",
            "hostname": "AlphaGSM wetcfg",
            "port": 27961,
        }
    )
    cfg_dir = tmp_path / "etmain"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "server.cfg"
    cfg_path.write_text(
        'set dedicated "2"\n// set net_port "27960"\nset sv_hostname "ETHost"\nexec campaigncycle.cfg\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert cfg_path.read_text(encoding="utf-8") == (
        'set dedicated "2"\n'
        'set net_port "27961"\n'
        'set sv_hostname "AlphaGSM wetcfg"\n'
        'exec campaigncycle.cfg\n'
    )


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Linux/x86/etded.x86",
            "fs_game": "etmain",
            "hostname": "AlphaGSM wet",
            "port": 27960,
            "configfile": "server.cfg",
        }
    )
    exe_path = tmp_path / "bin" / "Linux" / "x86"
    exe_path.mkdir(parents=True)
    (exe_path / "etded.x86").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./bin/Linux/x86/etded.x86",
        "+set",
        "net_strict",
        "1",
        "+set",
        "fs_homepath",
        server.data["dir"],
        "+set",
        "fs_game",
        "etmain",
        "+set",
        "net_port",
        "27960",
        "+set",
        "sv_hostname",
        "AlphaGSM wet",
        "+exec",
        "server.cfg",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_relative_fs_homepath_for_docker(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Linux/x86/etded.x86",
            "fs_game": "etmain",
            "hostname": "AlphaGSM wet",
            "port": 27960,
            "configfile": "server.cfg",
            "runtime": "docker",
        }
    )
    exe_path = tmp_path / "bin" / "Linux" / "x86"
    exe_path.mkdir(parents=True)
    (exe_path / "etded.x86").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./bin/Linux/x86/etded.x86",
        "+set",
        "net_strict",
        "1",
        "+set",
        "fs_homepath",
        ".",
        "+set",
        "fs_game",
        "etmain",
        "+set",
        "net_port",
        "27960",
        "+set",
        "sv_hostname",
        "AlphaGSM wet",
        "+exec",
        "server.cfg",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_missing_executable(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "bin/Linux/x86/etded.x86",
            "fs_game": "etmain",
            "hostname": "AlphaGSM wet",
            "port": 27960,
            "configfile": "server.cfg",
        }
    )
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_query_and_info_addresses_use_quake_protocol():
    server = DummyServer()
    server.data["port"] = 27960
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 27960, "quake")
        assert mod.get_info_address(server) == ("127.0.0.1", 27960, "quake")


def test_runtime_requirements_family():
    server = DummyServer()
    server.data.update({"dir": "/tmp/test/", "port": 27960})
    req = mod.get_runtime_requirements(server)
    assert req["family"] == "quake-linux"
    assert req["ports"][0] == {"host": 27960, "container": 27960, "protocol": "udp"}


def test_do_stop_uses_quit_command():
    server = DummyServer()
    with patch.object(mod.runtime_module, "send_to_server") as send_to_server:
        mod.do_stop(server, 0)
    send_to_server.assert_called_once_with(server, "\nquit\n")


def test_checkvalue_port():
    server = DummyServer()
    assert mod.checkvalue(server, ("port",), "27960") == 27960


def test_checkvalue_hostname():
    server = DummyServer()
    assert mod.checkvalue(server, ("hostname",), "Wet Host") == "Wet Host"
