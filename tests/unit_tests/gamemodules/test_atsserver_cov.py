"""Full coverage tests for atsserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.atsserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.atsserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["configdir"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "bin/linux_x64/americantruck_server"
    server.data["Steam_AppID"] = 2239530
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2239530
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2239530
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2239530
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
    server.data["exe_name"] = "bin/linux_x64/americantruck_server"
    server.data["configdir"] = ".local/share/American Truck Simulator"
    exe_path = tmp_path / "bin/linux_x64/americantruck_server"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    cmd, cwd = mod.get_start_command(server)
    assert cmd[:2] == ["env", "XDG_DATA_HOME=" + str(tmp_path / ".local/share")]
    assert cmd[2:] == ["./bin/linux_x64/americantruck_server"]
    assert "-ip" not in cmd
    assert "-port" not in cmd
    assert "-query_port" not in cmd
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_prestart_rejects_missing_or_empty_exports(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    config_dir = tmp_path / server.data["configdir"]
    config_dir.mkdir(parents=True)
    (config_dir / "server_packages.sii").write_text("exported settings")

    with pytest.raises(ServerError, match="server_packages.dat") as missing:
        mod.prestart(server)
    message = str(missing.value)
    assert "ENABLED (BYO)" in message
    assert "server_packages.sii" in message
    assert "docs/servers/atsserver.md" in message

    (config_dir / "server_packages.dat").write_text("")
    with pytest.raises(ServerError, match="server_packages"):
        mod.prestart(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


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


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer()
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda srv: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.10", 27016, "a2s")


def test_checkvalue_configdir():
    server = DummyServer()
    result = mod.checkvalue(server, ("configdir",), "/test/value")
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


def test_sync_server_config_updates_ports_preserving_other_settings(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28015, dir=str(tmp_path))
    server.data["queryport"] = 28016
    config_dir = tmp_path / server.data["configdir"]
    config_dir.mkdir(parents=True)
    path = config_dir / "server_config.sii"
    path.write_text('SiiNunit\n{\nserver_config : _nameless.test {\n'
                    ' lobby_name: "My convoy"\n connection_dedicated_port: 27015\n'
                    ' query_dedicated_port: 27016\n}\n}\n')

    mod.sync_server_config(server)

    content = path.read_text()
    assert 'lobby_name: "My convoy"' in content
    assert "connection_dedicated_port: 28015" in content
    assert "query_dedicated_port: 28016" in content


def test_prestart_syncs_ports_when_exports_are_nonempty(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=28015, dir=str(tmp_path))
    server.data["queryport"] = 28016
    config_dir = tmp_path / server.data["configdir"]
    config_dir.mkdir(parents=True)
    for filename in ("server_packages.sii", "server_packages.dat"):
        (config_dir / filename).write_bytes(b"client export")

    mod.prestart(server)

    content = (config_dir / "server_config.sii").read_text()
    assert "connection_dedicated_port: 28015" in content
    assert "query_dedicated_port: 28016" in content


def test_custom_configdir_is_linked_into_native_linux_user_path(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    server.data["configdir"] = "custom-exports"

    mod.sync_server_config(server)

    native_path = tmp_path / ".alphagsm/ats-user-data/American Truck Simulator"
    assert native_path.is_symlink()
    assert native_path.resolve() == tmp_path / "custom-exports"
    assert (native_path / "server_config.sii").is_file()


def test_get_start_command_docker_home_stays_in_server_mount(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    executable = tmp_path / server.data["exe_name"]
    executable.parent.mkdir(parents=True)
    executable.touch()
    command, _cwd = mod.get_start_command(server)
    assert command[:2] == ["env", "XDG_DATA_HOME=" + str(tmp_path / ".local/share")]
    spec = mod.get_container_spec(server)
    assert str(tmp_path) not in str(spec["command"])
    assert "XDG_DATA_HOME=/srv/ats-data" in spec["command"]
    assert {
        "source": str(tmp_path / server.data["configdir"]),
        "target": "/srv/ats-data/American Truck Simulator",
        "mode": "rw",
    } in spec["mounts"]
    assert mod.get_query_address(server)[2] == "a2s"
    assert mod.get_info_address(server)[2] == "a2s"


def test_runtime_requirements_before_configuration():
    server = DummyServer()
    server.data.clear()

    requirements = mod.get_runtime_requirements(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert not requirements.get("mounts")
