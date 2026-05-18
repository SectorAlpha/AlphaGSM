"""Focused coverage tests for hcuserver."""

from pathlib import Path
from unittest.mock import patch

import pytest

import gamemodules.hcuserver as mod
from server import ServerError


class DummyData(dict):
    def save(self):
        pass


class DummyServer:
    def __init__(self, name="hcutest"):
        self.name = name
        self.data = DummyData()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7778, dir=str(tmp_path))
    assert server.data["port"] == 7778
    assert "queryport" not in server.data
    assert server.data["exe_name"] == "UnboxedServer.sh"
    assert server.data["Steam_AppID"] == mod.steam_app_id


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "UnboxedServer.sh", "port": 7777})
    (tmp_path / "UnboxedServer.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./UnboxedServer.sh",
        "-MultiHome=0.0.0.0",
        "-Port=7777",
        "-log",
        "-unattended",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_missing_executable(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "UnboxedServer.sh", "port": 7777})
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_query_and_info_addresses():
    server = DummyServer()
    server.data["port"] = 7777
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 7777, "udp")
        assert mod.get_info_address(server) == ("127.0.0.1", 7777, "udp")


def test_runtime_requirements_family():
    server = DummyServer()
    server.data.update({"dir": "/tmp/hcu/", "port": 7777})
    req = mod.get_runtime_requirements(server)
    assert req["family"] == "steamcmd-linux"


def test_checkvalue_port():
    server = DummyServer()
    assert mod.checkvalue(server, ("port",), "7777") == 7777


def test_ensure_launch_files_executable(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "UnboxedServer.sh"})
    script = tmp_path / "UnboxedServer.sh"
    binary = tmp_path / "Unboxed" / "Binaries" / "Linux" / "UnboxedServer-Linux-Shipping"
    binary.parent.mkdir(parents=True)
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.write_text("", encoding="utf-8")

    mod._ensure_launch_files_executable(server)

    assert script.is_file()
    assert binary.is_file()