"""Focused unit coverage for ns2cserver."""

import posixpath
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


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
    assert (tmp_path / "logs").is_dir()


def test_get_start_command_builds_expected_linux_args(tmp_path):
    server = DummyServer("itns2cserver")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    exe_path = tmp_path / "ia32" / "ns2combatserver_linux32"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "./ns2combatserver_linux32",
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
        "-config_path",
        "../itns2cserver",
        "-logdir",
        "../logs",
        "-modstorage",
        "../itns2cserver/Workshop",
    ]
    assert cwd == str(tmp_path / "ia32")


def test_process_and_container_use_identical_game_argv_and_ia32_cwd(tmp_path):
    server = DummyServer("itns2cserver")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    exe_path = tmp_path / "ia32" / "ns2combatserver_linux32"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert docker_command == process_command
    assert docker_cwd == process_cwd == str(tmp_path / "ia32")
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server/ia32"


@pytest.mark.parametrize(
    (
        "layout",
        "configured_name",
        "relative_executable_dir",
        "container_cwd",
        "config_path",
        "log_path",
        "modstorage_path",
    ),
    (
        (
            "root",
            "ns2combatserver_linux32",
            ".",
            "/srv/server",
            "./linkedrootcombat",
            "./logs",
            "./linkedrootcombat/Workshop",
        ),
        (
            "ia32",
            "ia32/ns2combatserver_linux32",
            "ia32",
            "/srv/server/ia32",
            "../linkedrootcombat",
            "../logs",
            "../linkedrootcombat/Workshop",
        ),
        (
            "deep",
            "ia32/ns2combatserver_linux32",
            "legacy/bin",
            "/srv/server/legacy/bin",
            "../../linkedrootcombat",
            "../../logs",
            "../../linkedrootcombat/Workshop",
        ),
    ),
)
def test_symlinked_install_root_maps_resolved_process_cwd_into_container(
    tmp_path,
    layout,
    configured_name,
    relative_executable_dir,
    container_cwd,
    config_path,
    log_path,
    modstorage_path,
):
    real_install_dir = tmp_path / "payload" / layout
    real_install_dir.mkdir(parents=True)
    install_link = tmp_path / ("linked-" + layout)
    install_link.symlink_to(real_install_dir, target_is_directory=True)
    server = DummyServer("linkedrootcombat")
    mod.configure(
        server,
        ask=False,
        port=27015,
        dir=str(install_link),
        exe_name=configured_name,
    )
    executable_dir = real_install_dir / relative_executable_dir
    executable_dir.mkdir(parents=True, exist_ok=True)
    executable = executable_dir / "ns2combatserver_linux32"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    container_spec = mod.get_container_spec(server)

    assert process_command[0] == "./ns2combatserver_linux32"
    assert process_cwd.rstrip("/") == str(executable_dir)
    assert process_command[process_command.index("-config_path") + 1] == config_path
    assert process_command[process_command.index("-logdir") + 1] == log_path
    assert process_command[process_command.index("-modstorage") + 1] == modstorage_path
    assert container_spec["command"] == process_command
    assert container_spec["working_dir"] == container_cwd
    assert posixpath.normpath(posixpath.join(container_cwd, config_path)) == (
        "/srv/server/linkedrootcombat"
    )
    assert posixpath.normpath(posixpath.join(container_cwd, log_path)) == (
        "/srv/server/logs"
    )
    assert posixpath.normpath(posixpath.join(container_cwd, modstorage_path)) == (
        "/srv/server/linkedrootcombat/Workshop"
    )


def test_get_start_command_targets_instance_from_root_launcher(tmp_path):
    server = DummyServer("rootcombat")
    mod.configure(
        server,
        ask=False,
        port=27015,
        dir=str(tmp_path),
        exe_name="ns2combatserver_linux32",
    )
    (tmp_path / "ns2combatserver_linux32").write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert process_command[0] == "./ns2combatserver_linux32"
    assert process_command[process_command.index("-config_path") + 1] == "./rootcombat"
    assert process_command[process_command.index("-logdir") + 1] == "./logs"
    assert process_command[process_command.index("-modstorage") + 1] == (
        "./rootcombat/Workshop"
    )
    assert docker_command == process_command
    assert docker_cwd == process_cwd == str(tmp_path) + "/"
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server"


def test_deep_fallback_uses_paths_relative_to_resolved_working_dir(tmp_path):
    server = DummyServer("deepcombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    executable = tmp_path / "legacy" / "bin" / "ns2combatserver_linux32"
    executable.parent.mkdir(parents=True)
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert process_command[0] == "./ns2combatserver_linux32"
    assert process_command[process_command.index("-config_path") + 1] == "../../deepcombat"
    assert process_command[process_command.index("-logdir") + 1] == "../../logs"
    assert process_command[process_command.index("-modstorage") + 1] == (
        "../../deepcombat/Workshop"
    )
    assert docker_command == process_command
    assert docker_cwd == process_cwd == str(executable.parent)
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server/legacy/bin"


def test_in_tree_executable_symlink_keeps_resolved_launcher_context(tmp_path):
    server = DummyServer("linkedcombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    target = tmp_path / "payload" / "bin" / "ns2combatserver_linux32"
    target.parent.mkdir(parents=True)
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    configured = tmp_path / "ia32" / "ns2combatserver_linux32"
    configured.parent.mkdir()
    configured.symlink_to(target)

    process_command, process_cwd = mod.get_start_command(server)
    server.data["runtime"] = "docker"
    docker_command, docker_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert process_command[process_command.index("-config_path") + 1] == "../../linkedcombat"
    assert process_command[process_command.index("-logdir") + 1] == "../../logs"
    assert process_command[process_command.index("-modstorage") + 1] == (
        "../../linkedcombat/Workshop"
    )
    assert docker_command == process_command
    assert docker_cwd == process_cwd == str(target.parent)
    assert spec["command"] == process_command
    assert spec["working_dir"] == "/srv/server/payload/bin"


def test_external_executable_symlink_is_rejected(tmp_path):
    install_dir = tmp_path / "server"
    install_dir.mkdir()
    external_executable = tmp_path / "external" / "ns2combatserver_linux32"
    external_executable.parent.mkdir()
    external_executable.write_text("#!/bin/sh\n", encoding="utf-8")
    configured = install_dir / "ia32" / "ns2combatserver_linux32"
    configured.parent.mkdir()
    configured.symlink_to(external_executable)
    server = DummyServer("escapedcombat")
    mod.configure(server, ask=False, port=27015, dir=str(install_dir))

    with pytest.raises(ServerError, match="outside the install directory"):
        mod.get_start_command(server)


@pytest.mark.parametrize(
    "configured_dir",
    ("logs", "config", "instance", "instance-workshop"),
)
def test_configured_symlink_rejects_unsafe_lexical_location(
    tmp_path,
    configured_dir,
):
    server = DummyServer("lexicalcombat")
    relative_dir = {
        "logs": "logs",
        "config": "config",
        "instance": server.name,
        "instance-workshop": server.name + "/Workshop",
    }[configured_dir]
    exe_name = relative_dir + "/ns2combatserver_linux32"
    mod.configure(
        server,
        ask=False,
        port=27015,
        dir=str(tmp_path),
        exe_name=exe_name,
    )
    safe_target = tmp_path / "payload" / "bin" / "ns2combatserver_linux32"
    safe_target.parent.mkdir(parents=True)
    safe_target.write_text("#!/bin/sh\n", encoding="utf-8")
    configured = tmp_path / exe_name
    configured.parent.mkdir(parents=True, exist_ok=True)
    configured.symlink_to(safe_target)

    with pytest.raises(ServerError, match="safe install payload"):
        mod.get_start_command(server)


@pytest.mark.parametrize("data_dir", ("logs", "config"))
def test_recursive_fallback_rejects_data_directories(tmp_path, data_dir):
    server = DummyServer("datacombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    executable = tmp_path / data_dir / "ns2combatserver_linux32"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")

    with pytest.raises(ServerError, match="safe install payload"):
        mod.get_start_command(server)


def test_recursive_fallback_ignores_instance_workshop_candidate(tmp_path):
    server = DummyServer("instancecombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    unsafe = tmp_path / server.name / "Workshop" / "ns2combatserver_linux32"
    unsafe.parent.mkdir(parents=True)
    unsafe.write_text("#!/bin/sh\n", encoding="utf-8")
    safe = tmp_path / "payload" / "bin" / "ns2combatserver_linux32"
    safe.parent.mkdir(parents=True)
    safe.write_text("#!/bin/sh\n", encoding="utf-8")

    command, cwd = mod.get_start_command(server)

    assert command[0] == "./ns2combatserver_linux32"
    assert cwd == str(safe.parent)


def test_recursive_fallback_rejects_ambiguous_safe_candidates(tmp_path):
    server = DummyServer("ambiguouscombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    for directory in (tmp_path / "payload-a" / "bin", tmp_path / "payload-b" / "bin"):
        directory.mkdir(parents=True)
        (directory / "ns2combatserver_linux32").write_text(
            "#!/bin/sh\n",
            encoding="utf-8",
        )

    with pytest.raises(ServerError, match="ambiguous"):
        mod.get_start_command(server)


@pytest.mark.parametrize("configured_kind", ("broken-symlink", "directory"))
def test_existing_invalid_configured_launcher_never_uses_fallback(
    tmp_path,
    configured_kind,
):
    server = DummyServer("invalidconfiguredcombat")
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    configured = tmp_path / "ia32" / "ns2combatserver_linux32"
    configured.parent.mkdir(parents=True)
    if configured_kind == "broken-symlink":
        configured.symlink_to(tmp_path / "missing" / "ns2combatserver_linux32")
    else:
        configured.mkdir()
    fallback = tmp_path / "payload" / "bin" / "ns2combatserver_linux32"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("#!/bin/sh\n", encoding="utf-8")

    with pytest.raises(ServerError, match="not a regular file"):
        mod.get_start_command(server)


def test_query_info_and_runtime_ports_use_a2s_on_game_port_plus_one(monkeypatch):
    server = DummyServer()
    server.data.update({"port": 27015, "httpport": 8080})
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda _server: "10.0.0.9")

    assert mod.get_query_address(server) == ("10.0.0.9", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.9", 27016, "a2s")
    assert mod.get_runtime_requirements(server)["ports"] == [
        {"host": 27015, "container": 27015, "protocol": "udp"},
        {"host": 27016, "container": 27016, "protocol": "udp"},
        {"host": 8080, "container": 8080, "protocol": "tcp"},
    ]


def test_get_start_command_requires_executable(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))

    with pytest.raises(ServerError):
        mod.get_start_command(server)
