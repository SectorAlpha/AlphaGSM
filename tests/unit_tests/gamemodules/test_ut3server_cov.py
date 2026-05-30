"""Focused coverage tests for ut3server."""

from unittest.mock import patch

import pytest

import gamemodules.ut3server as mod
from server import ServerError


class DummyData(dict):
    def save(self):
        pass


class DummyServer:
    def __init__(self, name="ut3test"):
        self.name = name
        self.data = DummyData()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7778, dir=str(tmp_path))
    assert server.data["port"] == 7778
    assert server.data["queryport"] == "6500"
    assert server.data["exe_name"] == "Binaries/ut3"
    assert server.data["defaultmap"] == "VCTF-Suspense"


def test_get_start_command(tmp_path):
    server = DummyServer("ut3cfg")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Binaries/ut3",
            "port": 7777,
            "queryport": 6500,
            "defaultmap": "VCTF-Suspense",
            "game": "UTGameContent.UTVehicleCTFGame_Content",
            "mutators": "",
            "isdedicated": "true",
            "islanmatch": "false",
            "usesstats": "false",
            "shouldadvertise": "true",
            "pureserver": "1",
            "allowjoininprogress": "true",
            "gsusername": "user",
            "gspassword": "pass",
        }
    )
    exe_path = tmp_path / "Binaries"
    exe_path.mkdir(parents=True)
    (exe_path / "ut3").write_text("", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./Binaries/ut3",
        "server",
        "VCTF-Suspense?Game=UTGameContent.UTVehicleCTFGame_Content?bIsDedicated=true?bIsLanMatch=false?bUsesStats=false?bShouldAdvertise=true?PureServer=1?bAllowJoinInProgress=true?ConfigSubDir=ut3cfg",
        "-login=user",
        "-password=pass",
        "-multihome=0.0.0.0",
        "-port=7777",
        "-queryport=6500",
        "-nohomedir",
        "-unattended",
        "-log=server.log",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_missing_executable(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Binaries/ut3", "port": 7777})
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_install_missing_owned_files_raises_byo(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "Binaries/ut3"})
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\)"):
        mod.install(server)


def test_query_and_info_addresses_use_ut3_protocol():
    server = DummyServer()
    server.data["queryport"] = 6500
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 6500, "ut3")
        assert mod.get_info_address(server) == ("127.0.0.1", 6500, "ut3")


def test_runtime_requirements_family():
    server = DummyServer()
    server.data.update({"dir": "/tmp/ut3/", "port": 7777, "queryport": 6500})
    req = mod.get_runtime_requirements(server)
    assert req["family"] == "steamcmd-linux"


def test_checkvalue_port_and_queryport():
    server = DummyServer()
    assert mod.checkvalue(server, ("port",), "7777") == 7777
    assert mod.checkvalue(server, ("queryport",), "6500") == 6500
