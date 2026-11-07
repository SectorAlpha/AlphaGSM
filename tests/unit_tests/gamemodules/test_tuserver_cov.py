"""Focused unit coverage for tuserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


sys.modules.pop("gamemodules.tuserver", None)
sys.modules.pop("gamemodules.tuserver.main", None)
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
    import gamemodules.tuserver as mod
    from server import ServerError


def test_configure_sets_defaults(tmp_path):
    server = DummyServer("ittu")

    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 439660
    assert server.data["queryport"] == "27015"
    assert server.data["exe_name"] == "Tower/Binaries/Linux/TowerServer-Linux-Shipping"


def test_install_creates_instance_config_from_template(tmp_path):
    server = DummyServer("ittu")
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    config_dir = tmp_path / "Tower" / "Binaries" / "Linux"
    config_dir.mkdir(parents=True)
    (config_dir / "TowerServer.ini").write_text("ServerName=Tower\n", encoding="utf-8")

    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_count == 1
    assert download.call_args.args[:3] == (str(tmp_path) + "/", mod.steam_app_id, True)
    assert (config_dir / "ittu.ini").read_text(encoding="utf-8") == "ServerName=Tower\n"


def test_get_start_command_includes_instance_config_and_queryport(tmp_path):
    server = DummyServer("ittu")
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    exe_path = tmp_path / "Tower" / "Binaries" / "Linux" / "TowerServer-Linux-Shipping"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./Tower/Binaries/Linux/TowerServer-Linux-Shipping",
        "-MultiHome=0.0.0.0",
        "-Port=7777",
        "-QueryPort=27015",
        "-TowerServerINI=ittu.ini",
        "-nosteamclient",
        "-log",
    ]
    assert cwd == str(tmp_path) + "/"


def test_query_and_info_addresses_use_queryport():
    server = DummyServer("ittu")
    server.data.update({"port": 7777, "queryport": "27015"})

    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "a2s")


def test_get_start_command_requires_executable(tmp_path):
    server = DummyServer("ittu")
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_prestart_stages_bundled_steamclient_next_to_executable(tmp_path):
    server = DummyServer("ittu")
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    source = tmp_path / "linux64" / "steamclient.so"
    source.parent.mkdir()
    source.write_bytes(b"current bundled steam client")
    destination = tmp_path / "Tower" / "Binaries" / "Linux" / "steamclient.so"
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"outdated steam client")

    mod.prestart(server)

    assert destination.read_bytes() == source.read_bytes()
    assert not destination.is_symlink()


def test_prestart_reports_missing_steamclient(tmp_path):
    server = DummyServer("ittu")
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    with pytest.raises(ServerError, match="steamclient.so"):
        mod.prestart(server)
