"""Focused unit coverage for onsetserver."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


sys.modules.pop("gamemodules.onsetserver", None)
sys.modules.pop("gamemodules.onsetserver.main", None)
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
    import gamemodules.onsetserver as mod
    from server import ServerError


def test_configure_sets_expected_defaults(tmp_path):
    server = DummyServer("itonsetserver")

    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert server.data["Steam_AppID"] == 1204170
    assert server.data["servername"] == "AlphaGSM itonsetserver"
    assert server.data["servername_short"] == "itonsetserver"
    assert server.data["gamemode"] == "Sandbox"
    assert server.data["queryport"] == 7776
    assert server.data["httpport"] == 7775
    assert server.data["exe_name"] == "start_linux.sh"


def test_install_downloads_and_writes_server_config(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    exe_path = tmp_path / "start_linux.sh"
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_count == 1
    assert download.call_args.args[:3] == (str(tmp_path) + "/", mod.steam_app_id, True)
    config = json.loads((tmp_path / "server_config.json").read_text(encoding="utf-8"))
    assert config["port"] == 7777
    assert config["packages"] == ["sandbox"]
    assert config["masterlist"] is False


def test_get_start_command_uses_config_flag_and_query_port(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    exe_path = tmp_path / "start_linux.sh"
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./start_linux.sh",
        "--config",
        str(tmp_path / "server_config.json"),
    ]
    assert cwd == str(tmp_path) + "/"
    assert mod.get_query_address(server) == ("127.0.0.1", 7776, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 7776, "a2s")


def test_get_start_command_uses_relative_config_for_docker(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    server.data["runtime"] = "docker"
    exe_path = tmp_path / "start_linux.sh"
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == ["./start_linux.sh", "--config", "server_config.json"]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_prefers_resolved_nested_launcher_for_docker(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    server.data["runtime"] = "docker"
    nested_dir = tmp_path / "bin"
    nested_dir.mkdir()
    nested_exe = nested_dir / "start_linux.sh"
    nested_exe.write_text("#!/bin/sh\n", encoding="utf-8")
    os.symlink(nested_exe, tmp_path / "start_linux.sh")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == ["./start_linux.sh", "--config", "../server_config.json"]
    assert cwd == str(nested_dir)


def test_checkvalue_recalculates_derived_ports(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    server.data["port"] = mod.checkvalue(server, "port", "9000")
    mod.sync_server_config(server)

    assert server.data["port"] == 9000
    assert server.data["queryport"] == 8999
    assert server.data["httpport"] == 8998


def test_get_start_command_requires_executable(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_runtime_requirements_declare_linux_openssl_11():
    server = DummyServer()
    server.data.update({"port": 7777, "queryport": 7776, "httpport": 7775})
    requirements = mod.get_runtime_requirements(server)
    dependency = next(
        item for item in requirements["host_dependencies"] if item["id"] == "openssl-1.1"
    )
    assert dependency["kind"] == "shared-library"
    assert dependency["library_names"]["linux"] == "libssl.so.1.1"
    assert dependency["platforms"] == ["linux"]
