"""Full coverage tests for silicaserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.silicaserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.silicaserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
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
    server.data["exe_name"] = "Silica.x86_64"
    server.data["Steam_AppID"] = 2738040
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2738040
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2738040
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2738040
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
    server.data["exe_name"] = "Silica.x86_64"
    (tmp_path / "Silica.x86_64").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


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


def test_native_xml_sync_preserves_operator_settings(tmp_path):
    import xml.etree.ElementTree as etree
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=19000, queryport=19001,
                       maxplayers=12, servername='Alpha & Friends')
    config = tmp_path / '.alphagsm-home/Silica/ServerSettings.xml'
    config.parent.mkdir(parents=True)
    config.write_text('<NetworkServerSettings ServerName="Old" CurrentGameMode="MP_Strategy" '
                      'GamePort="26900" QueryPort="26901" CustomOption="preserved">'
                      '<GameModeSettings GameMode="MP_Strategy" CurrentMap="IndustrialQuarter" MaxPlayers="8" />'
                      '<GameModeSettings GameMode="MP_Sandbox" MaxPlayers="4" />'
                      '<Admins><Admin Name="operator" /></Admins></NetworkServerSettings>')
    mod.sync_server_config(server)
    root = etree.parse(config).getroot()
    assert root.attrib['GamePort'] == '19000'
    assert root.attrib['QueryPort'] == '19001'
    assert root.attrib['ServerName'] == 'Alpha & Friends'
    assert root.attrib['CustomOption'] == 'preserved'
    assert root.find("GameModeSettings[@GameMode='MP_Strategy']").attrib == {
        'GameMode': 'MP_Strategy', 'CurrentMap': 'IndustrialQuarter', 'MaxPlayers': '12'}
    assert root.find("GameModeSettings[@GameMode='MP_Sandbox']").attrib['MaxPlayers'] == '4'
    assert root.find('Admins/Admin').attrib['Name'] == 'operator'
    assert set(('port', 'queryport', 'maxplayers', 'servername')) <= set(mod.config_sync_keys)


def test_process_command_uses_isolated_home_and_no_guessed_game_flags(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name='Silica.x86_64')
    (tmp_path / 'Silica.x86_64').touch()
    command, cwd = mod.get_start_command(server)
    assert command == ['env', f'HOME={tmp_path}/.alphagsm-home', './Silica.x86_64', '-batchmode', '-nographics']
    assert cwd == str(tmp_path)


def test_docker_home_mount_reads_the_same_native_config_as_process(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name='Silica.x86_64', port=19000, queryport=19001)
    (tmp_path / 'Silica.x86_64').touch()
    monkeypatch.setattr(mod.runtime_module, '_running_inside_container', lambda: False)
    monkeypatch.setattr(mod.runtime_module, '_current_container_bind_mounts', lambda: [])
    spec = mod.get_container_spec(server)
    assert spec['env']['HOME'] == '/root'
    assert {'source': f'{tmp_path}/.alphagsm-home', 'target': '/root', 'mode': 'rw'} in spec['mounts']
    assert spec['command'] == ['./Silica.x86_64', '-batchmode', '-nographics']
    assert not any(str(tmp_path) in argument for argument in spec['command'])


def test_fresh_native_config_and_process_sdk_use_isolated_home(tmp_path, monkeypatch):
    import xml.etree.ElementTree as etree
    server = DummyServer()
    server.data.update(dir=str(tmp_path / 'server'), port=19000, queryport=19001,
                       maxplayers=16, servername='Fresh server')
    sdk = tmp_path / 'steamcmd/linux64'
    sdk.mkdir(parents=True)
    (sdk / 'steamclient.so').write_bytes(b'fixture Steam SDK')
    monkeypatch.setattr(mod.steamcmd, 'STEAMCMD_DIR', str(sdk.parent))
    monkeypatch.setattr(mod.os.path, 'expanduser', lambda _path: str(tmp_path / 'absent.xml'))
    mod.prestart(server)
    home = tmp_path / 'server/.alphagsm-home'
    root = etree.parse(home / 'Silica/ServerSettings.xml').getroot()
    assert root.attrib['GamePort'] == '19000'
    assert root.attrib['QueryPort'] == '19001'
    assert root.attrib['CurrentGameMode'] == 'MP_Strategy'
    assert root.find('GameModeSettings').attrib['MaxPlayers'] == '16'
    assert (home / '.steam/sdk64/steamclient.so').read_bytes() == b'fixture Steam SDK'
    mod.prestart(server)
    assert (home / '.steam/sdk64/steamclient.so').is_symlink()


def test_docker_home_keeps_shared_steam_sdk_mount(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name='Silica.x86_64', port=19000, queryport=19001)
    (tmp_path / 'Silica.x86_64').touch()
    sdk = tmp_path / 'steamcmd/linux64'
    sdk.mkdir(parents=True)
    (sdk / 'steamclient.so').touch()
    monkeypatch.setattr(mod.runtime_module.steamcmd_module, 'STEAMCMD_DIR', str(sdk.parent))
    monkeypatch.setattr(mod.runtime_module, '_running_inside_container', lambda: True)
    monkeypatch.setattr(mod.runtime_module, '_current_container_bind_mounts', lambda: [
        {'source': '/daemon/work', 'destination': str(tmp_path)}])
    spec = mod.get_container_spec(server)
    mounts = mod.runtime_module.validate_mount_path_identity(spec['mounts'])
    assert {'source': '/daemon/work/steamcmd/linux64', 'target': '/root/.steam/sdk64', 'mode': 'ro'} in mounts
    assert {'source': '/daemon/work/.alphagsm-home', 'target': '/root', 'mode': 'rw'} in mounts


def test_migration_preserves_original_operator_config(tmp_path, monkeypatch):
    original = tmp_path / 'operator.xml'
    original_text = '<NetworkServerSettings CurrentGameMode="MP_Sandbox" ServerPassword="keep">' \
        '<GameModeSettings GameMode="MP_Sandbox" CurrentMap="custom" MaxPlayers="4" />' \
        '</NetworkServerSettings>'
    original.write_text(original_text)
    monkeypatch.setattr(mod.os.path, 'expanduser', lambda _path: str(original))
    server = DummyServer()
    server.data.update(dir=str(tmp_path / 'server'), port=19000, queryport=19001, maxplayers=8)
    mod.sync_server_config(server)
    assert original.read_text() == original_text
    managed = tmp_path / 'server/.alphagsm-home/Silica/ServerSettings.xml'
    assert 'ServerPassword="keep"' in managed.read_text()
    assert 'CurrentMap="custom"' in managed.read_text()
    assert 'MaxPlayers="8"' in managed.read_text()


def test_invalid_native_xml_is_not_overwritten(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=19000)
    config = tmp_path / '.alphagsm-home/Silica/ServerSettings.xml'
    config.parent.mkdir(parents=True)
    config.write_text('<broken')
    with pytest.raises(ServerError, match='Invalid Silica server settings'):
        mod.sync_server_config(server)
    assert config.read_text() == '<broken'


def test_hostname_alias_and_query_endpoint_match_native_fields(monkeypatch):
    server = DummyServer()
    server.data.update(port=19000, queryport=19001)
    assert mod.checkvalue(server, ('hostname',), 'Server Name') == 'Server Name'
    monkeypatch.setattr(mod.runtime_module, 'resolve_query_host', lambda server: '192.0.2.7')
    assert mod.get_query_address(server) == ('192.0.2.7', 19001, 'a2s')
    assert mod.get_info_address(server) == ('192.0.2.7', 19001, 'a2s')
