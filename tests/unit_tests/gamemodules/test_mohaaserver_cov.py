"""Focused coverage tests for mohaaserver."""

from unittest.mock import patch

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

import gamemodules.mohaaserver as mod
from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer("mohaa")
    mod.configure(server, ask=False, port=12203, dir=str(tmp_path))
    assert server.data["port"] == 12203
    assert server.data["exe_name"] == "mohaa_lnxded"
    assert server.data["startmap"] == "dm/mohdm1"
    assert server.data["configfile"] == "main/mohaa.cfg"


def test_get_start_command(tmp_path):
    server = DummyServer("mohaa")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mohaa_lnxded",
            "port": 12203,
            "ip": "0.0.0.0",
            "startmap": "dm/mohdm1",
            "configfile": "main/mohaa.cfg",
        }
    )
    (tmp_path / "mohaa_lnxded").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./mohaa_lnxded",
        "+set",
        "sv_punkbuster",
        "0",
        "+set",
        "fs_basepath",
        server.data["dir"],
        "+set",
        "fs_outputpath",
        server.data["dir"] + "Logs",
        "+set",
        "dedicated",
        "2",
        "+set",
        "net_ip",
        "0.0.0.0",
        "+set",
        "net_port",
        "12203",
        "+map",
        "dm/mohdm1",
        "+exec",
        "main/mohaa.cfg",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_relative_paths_for_docker(tmp_path):
    server = DummyServer("mohaa")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "mohaa_lnxded",
            "port": 12203,
            "ip": "0.0.0.0",
            "startmap": "dm/mohdm1",
            "configfile": "main/mohaa.cfg",
            "runtime": "docker",
        }
    )
    (tmp_path / "mohaa_lnxded").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd[6] == "."
    assert cmd[9] == "./Logs"
    assert cwd == server.data["dir"]


def test_get_start_command_missing_executable(tmp_path):
    server = DummyServer("mohaa")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "mohaa_lnxded", "port": 12203})
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_install_missing_owned_files_raises_byo(tmp_path):
    server = DummyServer("mohaa")
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "mohaa_lnxded"})
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\)"):
        mod.install(server)


def test_query_and_info_addresses_use_udp():
    server = DummyServer("mohaa")
    server.data["port"] = 12203
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 12203, "udp")
        assert mod.get_info_address(server) == ("127.0.0.1", 12203, "udp")


def test_runtime_requirements_family():
    server = DummyServer("mohaa")
    server.data.update({"dir": "/tmp/mohaa/", "port": 12203})
    req = mod.get_runtime_requirements(server)
    assert req["family"] == "quake-linux"


def test_checkvalue_port():
    server = DummyServer("mohaa")
    assert mod.checkvalue(server, ("port",), "12203") == 12203
