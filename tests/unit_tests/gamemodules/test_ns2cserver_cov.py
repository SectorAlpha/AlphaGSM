"""Focused unit coverage for ns2cserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest


sys.modules.pop("gamemodules.ns2cserver", None)
sys.modules.pop("gamemodules.ns2cserver.main", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.fileutils": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.ns2cserver as mod
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
    def __init__(self, name="itns2cserver"):
        self.name = name
        self.data = DummyData()

    def stop(self):
        return None

    def start(self):
        return None


def test_configure_sets_expected_defaults(tmp_path):
    server = DummyServer()

    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 313900
    assert server.data["startmap"] == "co_core"
    assert server.data["maxplayers"] == "24"
    assert server.data["httpport"] == "8080"
    assert server.data["exe_name"] == "ia32/ns2combatserver_linux32"


def test_install_downloads_and_creates_instance_dirs(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_count == 1
    assert download.call_args.args[:3] == (str(tmp_path) + "/", mod.steam_app_id, True)
    assert (tmp_path / server.name).is_dir()
    assert (tmp_path / server.name / "Workshop").is_dir()


def test_get_start_command_builds_expected_linux_args(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    exe_path = tmp_path / "ia32" / "ns2combatserver_linux32"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./ia32/ns2combatserver_linux32",
        "-name",
        "AlphaGSM itns2cserver",
        "-port",
        "27015",
        "-webuser",
        "admin",
        "-webpassword",
        "CHANGE_ME",
        "-webport",
        "8080",
        "-map",
        "co_core",
        "-limit",
        "24",
        "-webadmin",
        "-webdomain",
        "0.0.0.0",
        "-config_path",
        str(tmp_path / server.name),
        "-modstorage",
        str(tmp_path / server.name / "Workshop"),
    ]
    assert cwd == str(tmp_path) + "/"


def test_query_and_info_use_a2s_on_game_port():
    server = DummyServer()
    server.data["port"] = 27015

    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "a2s")


def test_get_start_command_requires_executable(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)