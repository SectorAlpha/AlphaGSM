"""Focused coverage tests for sof2server."""

from unittest.mock import patch

import pytest

import gamemodules.sof2server as mod
from server import ServerError


class DummyData(dict):
    def save(self):
        pass


class DummyServer:
    def __init__(self, name="sof2"):
        self.name = name
        self.data = DummyData()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=20100, dir=str(tmp_path))
    assert server.data["port"] == 20100
    assert server.data["exe_name"] == "sof2ded"
    assert server.data["startmap"] == "mp_shop"
    assert server.data["configfile"] == "base/sof2.cfg"


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "sof2ded",
            "port": 20100,
            "ip": "0.0.0.0",
            "startmap": "mp_shop",
            "configfile": "base/sof2.cfg",
        }
    )
    (tmp_path / "sof2ded").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./sof2ded",
        "+set",
        "sv_punkbuster",
        "0",
        "+set",
        "dedicated",
        "2",
        "+set",
        "net_ip",
        "0.0.0.0",
        "+set",
        "net_port",
        "20100",
        "+exec",
        "base/sof2.cfg",
        "+map",
        "mp_shop",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_missing_executable(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "sof2ded", "port": 20100})
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_install_missing_owned_files_raises_byo(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "sof2ded"})
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\)"):
        mod.install(server)


def test_query_and_info_addresses_use_quake():
    server = DummyServer()
    server.data["port"] = 20100
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 20100, "quake")
        assert mod.get_info_address(server) == ("127.0.0.1", 20100, "quake")


def test_runtime_requirements_family():
    server = DummyServer()
    server.data.update({"dir": "/tmp/sof2/", "port": 20100})
    req = mod.get_runtime_requirements(server)
    assert req["family"] == "quake-linux"


def test_checkvalue_port():
    server = DummyServer()
    assert mod.checkvalue(server, ("port",), "20100") == 20100
