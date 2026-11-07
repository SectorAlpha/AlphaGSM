"""Focused unit coverage for ns2server."""

import posixpath
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
        "-startmodserver",
        "-config_path",
        "./itns2server",
        "-logdir",
        "./logs",
        "-modstorage",
        "./itns2server/Workshop",
    ]
    assert cwd == str(tmp_path) + "/"


def test_process_and_container_use_identical_game_argv_and_install_cwd(tmp_path):
    server = DummyServer("itns2server")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    exe_path = tmp_path / "x64" / "server_linux"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert docker_command == process_command
    assert docker_cwd == process_cwd == str(tmp_path) + "/"
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server"


def test_symlinked_install_root_preserves_process_command_in_container(tmp_path):
    real_install_dir = tmp_path / "payload" / "ns2"
    real_install_dir.mkdir(parents=True)
    install_link = tmp_path / "linked-ns2"
    install_link.symlink_to(real_install_dir, target_is_directory=True)
    server = DummyServer("linkedrootns2")
    mod.configure(server, ask=False, port=27015, dir=str(install_link))
    executable = real_install_dir / "x64" / "server_linux"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    container_spec = mod.get_container_spec(server)

    assert process_command[0] == "./x64/server_linux"
    assert process_cwd == str(install_link) + "/"
    config_path = process_command[process_command.index("-config_path") + 1]
    log_path = process_command[process_command.index("-logdir") + 1]
    modstorage_path = process_command[process_command.index("-modstorage") + 1]
    assert config_path == "./linkedrootns2"
    assert log_path == "./logs"
    assert modstorage_path == "./linkedrootns2/Workshop"
    assert container_spec["command"] == process_command
    assert container_spec["working_dir"] == "/srv/server"
    assert posixpath.normpath(
        posixpath.join(container_spec["working_dir"], config_path)
    ) == "/srv/server/linkedrootns2"
    assert posixpath.normpath(
        posixpath.join(container_spec["working_dir"], log_path)
    ) == "/srv/server/logs"
    assert posixpath.normpath(
        posixpath.join(container_spec["working_dir"], modstorage_path)
    ) == "/srv/server/linkedrootns2/Workshop"


def test_query_info_and_runtime_ports_use_a2s_on_game_port_plus_one(monkeypatch):
    server = DummyServer()
    server.data.update(
        {
            "port": 27015,
            "httpport": 8080,
            "modserverport": 27031,
        }
    )
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda _server: "10.0.0.8")

    assert mod.get_query_address(server) == ("10.0.0.8", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.8", 27016, "a2s")
    assert mod.get_runtime_requirements(server)["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27016, "container": 27016, "protocol": "udp"},
        {"host": 8080, "container": 8080, "protocol": "tcp"},
        {"host": 27031, "container": 27031, "protocol": "tcp"},
    ]


def test_get_start_command_requires_executable(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)


@pytest.mark.parametrize("path_kind", ("absolute", "parent"))
def test_get_start_command_rejects_executable_paths_outside_install(tmp_path, path_kind):
    outside = tmp_path.parent / "ns2-outside"
    outside.write_text("#!/bin/sh\n", encoding="utf-8")
    exe_name = str(outside) if path_kind == "absolute" else "../" + outside.name
    server = DummyServer("unsafe-ns2")
    mod.configure(
        server,
        ask=False,
        port=27015,
        dir=str(tmp_path),
        exe_name=exe_name,
    )

    with pytest.raises(ServerError, match="inside the install directory"):
        mod.get_start_command(server)


def test_get_start_command_rejects_external_executable_symlink(tmp_path):
    outside = tmp_path.parent / "external-ns2-server"
    outside.write_text("#!/bin/sh\n", encoding="utf-8")
    launcher = tmp_path / "x64" / "server_linux"
    launcher.parent.mkdir()
    launcher.symlink_to(outside)
    server = DummyServer("linked-ns2")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError, match="inside the install directory"):
        mod.get_start_command(server)


@pytest.mark.parametrize(
    "configured_dir",
    ("logs", "config", "instance", "nested-workshop"),
)
def test_get_start_command_rejects_mutable_data_launcher_location(
    tmp_path,
    configured_dir,
):
    server = DummyServer("lexical-ns2")
    relative_dir = {
        "logs": "payload/logs/bin",
        "config": "payload/config/bin",
        "instance": "payload/" + server.name + "/bin",
        "nested-workshop": "payload/Workshop/bin",
    }[configured_dir]
    exe_name = relative_dir + "/server_linux"
    mod.configure(
        server,
        ask=False,
        port=27015,
        dir=str(tmp_path),
        exe_name=exe_name,
    )
    safe_target = tmp_path / "payload" / "bin" / "server_linux"
    safe_target.parent.mkdir(parents=True)
    safe_target.write_text("#!/bin/sh\n", encoding="utf-8")
    configured = tmp_path / exe_name
    configured.parent.mkdir(parents=True, exist_ok=True)
    configured.symlink_to(safe_target)

    with pytest.raises(ServerError, match="safe install payload"):
        mod.get_start_command(server)
