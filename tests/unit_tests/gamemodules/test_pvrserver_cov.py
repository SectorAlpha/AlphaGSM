"""Full coverage tests for pvrserver."""

import subprocess as sp
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.pvrserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.pvrserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data['queryport'] == '8177'


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["map"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PavlovServer.sh"
    server.data["Steam_AppID"] = 622970
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_install_tolerates_steamcmd_0x602_when_executable_present(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PavlovServer.sh"
    (tmp_path / "PavlovServer.sh").write_text("")
    monkeypatch.setattr(
        mod.steamcmd,
        "download",
        MagicMock(
        side_effect=sp.CalledProcessError(
            1,
            ["steamcmd"],
            output="Error! App '622970' state is 0x602 after update job.",
        )),
    )

    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 622970
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 622970
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_tolerates_steamcmd_0x602_when_executable_present(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PavlovServer.sh"
    server.data["Steam_AppID"] = 622970
    server.data["Steam_anonymous_login_possible"] = True
    (tmp_path / "PavlovServer.sh").write_text("")
    monkeypatch.setattr(
        mod.steamcmd,
        "download",
        MagicMock(
        side_effect=sp.CalledProcessError(
            1,
            ["steamcmd"],
            output="Error! App '622970' state is 0x602 after update job.",
        )),
    )

    mod.update(server, validate=False, restart=False)

    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 622970
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PavlovServer.sh"
    (tmp_path / "PavlovServer.sh").write_text("")
    server.data["map"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./PavlovServer.sh",
        "-PORT=27015",
        "-Map=test",
    ]
    assert cwd == server.data["dir"]


def test_query_and_runtime_ports_follow_fixed_offset(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    assert mod.get_query_address(server)[1:] == (27415, "udp")
    assert mod.get_info_address(server)[1:] == (27415, "udp")

    requirements = mod.get_runtime_requirements(server)
    ports = {(entry["host"], entry["protocol"]) for entry in requirements["ports"]}
    assert (27015, "udp") in ports
    assert (27015, "tcp") in ports
    assert (27415, "udp") in ports
    assert (27415, "tcp") not in ports
    assert server.data["queryport"] == "27415"


def test_runtime_requirements_without_port_use_default_offset():
    server = DummyServer()

    requirements = mod.get_runtime_requirements(server)

    ports = {(entry["host"], entry["protocol"]) for entry in requirements["ports"]}
    assert (8177, "udp") in ports
    assert (8177, "tcp") not in ports
    assert server.data["queryport"] == "8177"


def test_get_container_spec_drops_root_before_launch(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PavlovServer.sh"
    (tmp_path / "PavlovServer.sh").write_text("")
    server.data["map"] = "test"
    server.data["port"] = 27015

    spec = mod.get_container_spec(server)

    assert spec["command"][0:2] == ["sh", "-lc"]
    assert "useradd -m -d /home/pavlov -s /bin/bash pavlov" in spec["command"][2]
    assert "chown -R pavlov:pavlov /home/pavlov /srv/server" in spec["command"][2]
    assert "export HOME=/home/pavlov USER=pavlov LOGNAME=pavlov" in spec["command"][2]
    assert "XDG_CONFIG_HOME=/home/pavlov/.config" in spec["command"][2]
    assert (
        "exec setpriv --reuid=$(id -u pavlov) --regid=$(id -g pavlov) "
        "--clear-groups ./PavlovServer.sh -PORT=27015 -Map=test"
    ) in spec["command"][2]
    assert "-QueryPort=" not in spec["command"][2]
    assert spec["working_dir"] == "/srv/server"


def test_setting_schema_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-PORT={value}"
    assert mod.setting_schema["queryport"].launch_arg_format is None
    assert mod.setting_schema["map"].launch_arg_format == "-Map={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["map"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_runtime_requirements_include_host_libcxx_dependency_hint():
    server = DummyServer()
    server.data["port"] = 27015

    requirements = mod.get_runtime_requirements(server)

    host_dependencies = requirements["host_dependencies"]
    assert len(host_dependencies) == 1
    assert host_dependencies[0]["id"] == "libcxx"
    assert host_dependencies[0]["kind"] == "shared-library"
    assert host_dependencies[0]["library_names"]["linux"] == "libc++.so.1"
    assert "libc++1" in host_dependencies[0]["install_hints"]["linux"]


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)


def test_message():
    server = DummyServer()
    mod.message(server, "hello")


def test_backup():
    server = DummyServer()
    server.data["dir"] = "/tmp/test/"
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.backup(server)


def test_checkvalue_empty_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ())


def test_checkvalue_unsupported_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")


def test_checkvalue_no_value():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",))


def test_checkvalue_port():
    server = DummyServer()
    result = mod.checkvalue(server, ("port",), "12345")
    assert result == 12345


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_map():
    server = DummyServer()
    result = mod.checkvalue(server, ("map",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
