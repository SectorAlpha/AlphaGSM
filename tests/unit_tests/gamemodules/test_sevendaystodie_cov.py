"""Full coverage tests for sevendaystodie."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.sevendaystodie', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.sevendaystodie as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=26900, dir=str(tmp_path))
    assert server.data['port'] == 26900


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 26900
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["configfile"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["26901", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "startserver.sh"
    server.data["Steam_AppID"] = 294420
    server.data["Steam_anonymous_login_possible"] = True
    server.data["configfile"] = "serverconfig.xml"
    server.data["port"] = 26900
    (tmp_path / "serverconfig.xml").write_text('<property name="ServerPort" value="26900"/>\n')
    mod.install(server)


def test_sync_server_config_updates_serverconfig_values(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["configfile"] = "serverconfig.xml"
    server.data["port"] = 26901
    server.data["servername"] = "AlphaGSM 7DTD Test"
    server.data["maxplayers"] = 12
    server.data["serverpassword"] = "secret"
    config_path = tmp_path / "serverconfig.xml"
    config_path.write_text(
        '<property name="ServerPort" value="26900"/>\n'
        '<property name="ServerName" value="Old Name"/>\n'
        '<property name="ServerMaxPlayerCount" value="8"/>\n'
        '<property name="ServerPassword" value=""/>\n'
        '<property name="Region" value="NorthAmericaEast"/>\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        '<property name="ServerPort" value="26901"/>',
        '<property name="ServerName" value="AlphaGSM 7DTD Test"/>',
        '<property name="ServerMaxPlayerCount" value="12"/>',
        '<property name="ServerPassword" value="secret"/>',
        '<property name="Region" value="NorthAmericaEast"/>',
    ]


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 294420
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 294420
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 294420
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
    server.data["exe_name"] = "startserver.sh"
    (tmp_path / "startserver.sh").write_text("")
    server.data["configfile"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_runtime_contract_publishes_required_port_range(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.runtime_module, "_steamcmd_sdk_mounts", lambda: [])
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "startserver.sh",
            "configfile": "serverconfig.xml",
            "port": 26900,
        }
    )
    (tmp_path / "startserver.sh").write_text("", encoding="utf-8")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    expected_ports = [
        {"host": 26900, "container": 26900, "protocol": "tcp"},
        {"host": 26900, "container": 26900, "protocol": "udp"},
        {"host": 26901, "container": 26901, "protocol": "udp"},
        {"host": 26902, "container": 26902, "protocol": "udp"},
        {"host": 26903, "container": 26903, "protocol": "udp"},
    ]
    assert requirements["ports"] == expected_ports
    assert spec["ports"] == expected_ports


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["configfile"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "16")
    assert result == 16


def test_checkvalue_configfile():
    server = DummyServer()
    result = mod.checkvalue(server, ("configfile",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM 7DTD")
    assert result == "AlphaGSM 7DTD"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "secret")
    assert result == "secret"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
