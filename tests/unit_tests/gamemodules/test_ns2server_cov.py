"""Focused unit coverage for ns2server."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


sys.modules.pop("gamemodules.ns2server", None)
sys.modules.pop("gamemodules.ns2server.main", None)
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
    import gamemodules.ns2server as mod
    from server import ServerError


def test_configure_sets_expected_defaults(tmp_path):
    server = DummyServer()

    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 4940
    assert server.data["startmap"] == "ns2_summit"
    assert server.data["maxplayers"] == "20"
    assert server.data["maxspectators"] == "5"
    assert server.data["modserverport"] == "27031"
    assert server.data["exe_name"] == "x64/server_linux"


def test_install_downloads_and_creates_instance_dirs(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_count == 1
    assert download.call_args.args[:3] == (str(tmp_path) + "/", mod.steam_app_id, True)
    assert (tmp_path / server.name).is_dir()
    assert (tmp_path / server.name / "Workshop").is_dir()
    assert (tmp_path / "logs").is_dir()


def test_get_start_command_builds_expected_linux_args(tmp_path):
    server = DummyServer("itns2server")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    exe_path = tmp_path / "x64" / "server_linux"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./x64/server_linux",
        "-name",
        "AlphaGSM itns2server",
        "-port",
        "27015",
        "-webuser",
        "admin",
        "-webpassword",
        "CHANGE_ME",
        "-webport",
        "8080",
        "-modserverport",
        "27031",
        "-map",
        "ns2_summit",
        "-limit",
        "20",
        "-speclimit",
        "5",
        "-webadmin",
        "-webdomain",
        "0.0.0.0",
        "-startmodserver",
        "-config_path",
        str(tmp_path / server.name),
        "-logdir",
        str(tmp_path / "logs"),
        "-modstorage",
        str(tmp_path / server.name / "Workshop"),
    ]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_uses_relative_paths_for_docker(tmp_path):
    server = DummyServer("itns2server")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    server.data["runtime"] = "docker"
    exe_path = tmp_path / "x64" / "server_linux"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./x64/server_linux",
        "-name",
        "AlphaGSM itns2server",
        "-port",
        "27015",
        "-webuser",
        "admin",
        "-webpassword",
        "CHANGE_ME",
        "-webport",
        "8080",
        "-modserverport",
        "27031",
        "-map",
        "ns2_summit",
        "-limit",
        "20",
        "-speclimit",
        "5",
        "-webadmin",
        "-webdomain",
        "0.0.0.0",
        "-startmodserver",
        "-config_path",
        "./itns2server",
        "-logdir",
        "./logs",
        "-modstorage",
        "./itns2server/Workshop",
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
