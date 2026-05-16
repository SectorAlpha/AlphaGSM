"""Focused unit coverage for tf2cserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest


sys.modules.pop("gamemodules.tf2cserver", None)
sys.modules.pop("gamemodules.tf2cserver.main", None)
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
    import gamemodules.tf2cserver as mod
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
    def __init__(self, name="testserver"):
        self.name = name
        self.data = DummyData()
        self._stopped = False
        self._started = False

    def stop(self):
        self._stopped = True

    def start(self):
        self._started = True


def test_configure_sets_tf2_support_dir(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    assert server.data["port"] == 27015
    assert server.data["supportdir"] == str(tmp_path / "tf")
    assert server.data["startmap"] == "4koth_frigid"


def test_install_downloads_base_app_and_tf2c(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    (tmp_path / "srcds.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_count == 2
    first_call = download.call_args_list[0]
    second_call = download.call_args_list[1]
    assert first_call.args[:3] == (str(tmp_path / "tf"), mod.base_steam_app_id, True)
    assert second_call.args[:3] == (str(tmp_path) + "/", mod.steam_app_id, True)


def test_get_start_command_includes_tf_path(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    server.data["clientport"] = 27005
    server.data["sourcetvport"] = 27020
    (tmp_path / "srcds.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd[:5] == ["./srcds.sh", "-game", "tf2classified", "-tf_path", str(tmp_path / "tf")]
    assert "+map" in cmd
    assert "4koth_frigid" in cmd
    assert cwd == str(tmp_path) + "/"


def test_checkvalue_supportdir_accepts_string():
    server = DummyServer()

    assert mod.checkvalue(server, ("supportdir",), "/srv/tf") == "/srv/tf"


def test_get_start_command_requires_launcher(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)