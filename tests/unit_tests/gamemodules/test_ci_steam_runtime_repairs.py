"""Replay missing Steam SDK mounts observed in Docker rechecks."""

from types import SimpleNamespace

from gamemodules import stnserver, wfserver
import server.runtime as runtime_module


def test_warfork_exposes_steamcmd_sdk_to_dedicated_server(tmp_path, monkeypatch):
    sdk = tmp_path / 'steamcmd' / 'linux64'
    sdk.mkdir(parents=True)
    (sdk / 'steamclient.so').write_bytes(b'sdk')
    monkeypatch.setattr(runtime_module.steamcmd_module, 'STEAMCMD_DIR', str(sdk.parent))
    install = tmp_path / 'server'
    install.mkdir()
    server = SimpleNamespace(name='warfork', data={'dir': str(install), 'port': 27960})

    requirements = wfserver.get_runtime_requirements(server)

    assert {'source': str(sdk), 'target': '/root/.steam/sdk64', 'mode': 'ro'} in requirements['mounts']
    assert requirements['ports'] == [{'host': 27960, 'container': 27960, 'protocol': 'udp'}]


def test_survive_the_nights_configures_distinct_game_and_query_ports(tmp_path, monkeypatch):
    server = SimpleNamespace(name='stn', data={'dir': str(tmp_path), 'port': 25000})
    monkeypatch.setattr(runtime_module, 'resolve_query_host', lambda _server: '127.0.0.1')
    stnserver.sync_server_config(server)

    config = (tmp_path / 'Config' / 'ServerConfig.txt').read_text()
    assert 'ServerPort=25000' in config
    assert 'QueryPort=25001' in config
    assert stnserver.get_query_address(server) == ('127.0.0.1', 25001, 'a2s')
    ports = stnserver.get_runtime_requirements(server)['ports']
    assert {'host': 25000, 'container': 25000, 'protocol': 'udp'} in ports
    assert {'host': 25001, 'container': 25001, 'protocol': 'udp'} in ports


def test_survive_the_nights_preserves_explicit_query_port_and_other_config(tmp_path):
    config_dir = tmp_path / 'Config'
    config_dir.mkdir()
    path = config_dir / 'ServerConfig.txt'
    path.write_text('ServerName="Keep me"\nServerPort=7950\nQueryPort=7951\n')
    server = SimpleNamespace(name='stn', data={'dir': str(tmp_path), 'port': 26000, 'queryport': 27000})
    stnserver.sync_server_config(server)
    assert path.read_text() == 'ServerName="Keep me"\nServerPort=26000\nQueryPort=27000\n'
