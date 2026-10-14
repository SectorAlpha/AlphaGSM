"""Space Engineers native world mod activation and ownership."""
from copy import deepcopy
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest
from gamemodules import seserver as module
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


def adapter():
    assert hasattr(module, 'MOD_SUPPORT'), 'Space Engineers needs native Workshop activation'
    from gamemodules.seserver import workshop
    return workshop


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(module.runtime_module, "check_server_running", lambda _: False)
    world = tmp_path / 'Saves/World'
    world.mkdir(parents=True)
    (tmp_path / 'SpaceEngineers-Dedicated.cfg').write_text(
        '<MyConfigDedicated><LoadWorld>Saves/World</LoadWorld><ServerName>Operator</ServerName></MyConfigDedicated>')
    (world / 'Sandbox.sbc').write_text('<MyObjectBuilder_Checkpoint><!-- operator --><Mods><ModItem Name="operator.sbm"><PublishedFileId>99</PublishedFileId><PublishedServiceName>Steam</PublishedServiceName></ModItem></Mods><SessionName>Keep</SessionName></MyObjectBuilder_Checkpoint>')
    (world / 'Sandbox_config.sbc').write_text('<MyObjectBuilder_WorldConfiguration><Mods/><SessionName>Keep</SessionName></MyObjectBuilder_WorldConfiguration>')
    return SimpleNamespace(name='se', data=DummyData(dir=str(tmp_path)), module=module)


def test_native_world_mods_preserve_operator_settings_and_cleanup_only_owned(server, tmp_path):
    ws = adapter()
    ws.apply_workshop(server, ['1521905890'])
    for name in ('Sandbox.sbc', 'Sandbox_config.sbc'):
        root = ET.parse(tmp_path / 'Saves/World' / name).getroot()
        added = root.find("Mods/ModItem[PublishedFileId='1521905890']")
        assert added is not None and added.findtext('PublishedServiceName') == 'Steam'
        assert root.findtext('SessionName') == 'Keep'
    ws.apply_workshop(server, [])
    text = (tmp_path / 'Saves/World/Sandbox.sbc').read_text()
    assert '1521905890' not in text and 'operator.sbm' in text and 'operator' in text
    assert '<ServerName>Operator</ServerName>' in (tmp_path / 'SpaceEngineers-Dedicated.cfg').read_text()


def test_world_escape_and_symlinks_are_refused_before_any_write(server, tmp_path):
    ws = adapter()
    config = tmp_path / 'SpaceEngineers-Dedicated.cfg'
    for path in ('../outside', 'Z:\\other\\world', '//remote/share/world'):
        config.write_text(f'<MyConfigDedicated><LoadWorld>{path}</LoadWorld></MyConfigDedicated>')
        with pytest.raises(ServerError): ws.apply_workshop(server, ['123'])
    config.write_text('<MyConfigDedicated><LoadWorld>Saves/link</LoadWorld></MyConfigDedicated>')
    (tmp_path / 'Saves/link').symlink_to(tmp_path / 'Saves/World', target_is_directory=True)
    with pytest.raises(ServerError, match='symlink'): ws.apply_workshop(server, ['123'])


def test_owned_entry_external_changes_and_unowned_collisions_preserved(server, tmp_path):
    ws = adapter()
    with pytest.raises(ServerError, match='Unowned'): ws.apply_workshop(server, ['99'])
    ws.apply_workshop(server, ['123'])
    path = tmp_path / 'Saves/World/Sandbox_config.sbc'
    changed = path.read_text().replace('123.sbm', 'operator-edited.sbm')
    path.write_text(changed)
    with pytest.raises(ServerError, match='externally'): ws.apply_workshop(server, [])
    assert path.read_text() == changed
    assert '123' in (tmp_path / 'Saves/World/Sandbox.sbc').read_text()


def test_malformed_xml_and_duplicate_item_ids_refused(server, tmp_path):
    ws = adapter()
    with pytest.raises(ServerError): ws.apply_workshop(server, ['123', '123'])
    path = tmp_path / 'Saves/World/Sandbox_config.sbc'
    path.write_text('<!DOCTYPE x [<!ENTITY escape "bad">]><MyObjectBuilder_WorldConfiguration/>')
    with pytest.raises(ServerError, match='entit'): ws.apply_workshop(server, ['123'])
    assert not server.data.get('spaceengineers_workshop')


def test_multi_file_failure_rolls_back_native_config_and_ownership(server, tmp_path, monkeypatch):
    ws = adapter()
    originals = {p: p.read_text() for p in (tmp_path / 'Saves/World').iterdir()}
    real = ws.write_managed_text
    count = 0
    def fail_once(current, relative, text):
        nonlocal count
        count += 1
        if count == 2: raise OSError('simulated disk failure')
        return real(current, relative, text)
    monkeypatch.setattr(ws, 'write_managed_text', fail_once)
    with pytest.raises(OSError): ws.apply_workshop(server, ['123'])
    assert all(path.read_text() == text for path, text in originals.items())
    assert not server.data.get('spaceengineers_workshop')


def test_autoapply_false_preserves_native_config(server, monkeypatch):
    adapter()
    server.data['mods'] = {'enabled': True, 'autoapply': False, 'desired': {'workshop': []}}
    calls = []
    monkeypatch.setattr(module.MOD_SUPPORT, 'apply_configured_mods', lambda _: calls.append(True))
    module.apply_automatic_mods(server)
    assert not calls


def test_first_setup_bootstraps_vendor_world_without_overwriting_existing_save(tmp_path):
    server = SimpleNamespace(name='se', data=DummyData(dir=str(tmp_path), port=27016, servername='Test SE', maxplayers=8), module=module)
    stock = tmp_path / 'Content/CustomWorlds/Empty World'
    stock.mkdir(parents=True)
    (stock / 'Sandbox.sbc').write_text('<MyObjectBuilder_Checkpoint><Mods/><SessionName>Stock</SessionName></MyObjectBuilder_Checkpoint>')
    (stock / 'Sandbox_config.sbc').write_text('<MyObjectBuilder_WorldConfiguration><Settings><OnlineMode>OFFLINE</OnlineMode></Settings><Mods/></MyObjectBuilder_WorldConfiguration>')
    module.sync_server_config(server)
    cfg = ET.parse(tmp_path / 'SpaceEngineers-Dedicated.cfg').getroot()
    world = adapter().configured_world(server, cfg)
    assert world == tmp_path / 'Saves/se'
    assert cfg.findtext('ServerPort') == '27016'
    assert cfg.findtext('ServerName') == 'Test SE'
    native = world / 'Sandbox_config.sbc'
    assert ET.parse(native).findtext('Settings/OnlineMode') == 'PUBLIC'
    native.write_text('<MyObjectBuilder_WorldConfiguration><SessionName>Operator save</SessionName></MyObjectBuilder_WorldConfiguration>')
    module.sync_server_config(server)
    assert 'Operator save' in native.read_text()
    assert 'OFFLINE' in (stock / 'Sandbox_config.sbc').read_text()


def test_bootstrap_refuses_vendor_symlink_and_existing_world_collision(tmp_path):
    server = SimpleNamespace(name='se', data=DummyData(dir=str(tmp_path), port=27016), module=module)
    stock = tmp_path / 'Content/CustomWorlds/Empty World'
    stock.mkdir(parents=True)
    (stock / 'Sandbox.sbc').symlink_to(tmp_path/'outside.xml')
    with pytest.raises(ServerError, match='symlink'): module.sync_server_config(server)


def test_bootstrap_write_failure_removes_only_its_new_world(tmp_path, monkeypatch):
    from gamemodules.seserver import configuration
    server = SimpleNamespace(name='se', data=DummyData(dir=str(tmp_path), port=27016), module=module)
    stock = tmp_path / 'Content/CustomWorlds/Empty World'
    stock.mkdir(parents=True)
    for name, tag in [('Sandbox.sbc','MyObjectBuilder_Checkpoint'),('Sandbox_config.sbc','MyObjectBuilder_WorldConfiguration')]:
        (stock/name).write_text(f'<{tag}><Mods/></{tag}>')
    monkeypatch.setattr(configuration, 'write_managed_text', lambda *_: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError): module.sync_server_config(server)
    assert not (tmp_path/'Saves/se').exists()
    assert (stock/'Sandbox.sbc').exists()


def test_linux_headless_uses_supported_no_console_mode(server, tmp_path, monkeypatch):
    executable = tmp_path/'DedicatedServer64/SpaceEngineersDedicated.exe'
    executable.parent.mkdir()
    executable.write_bytes(b'fixture')
    server.data['port'] = 27016
    monkeypatch.setattr(module, 'IS_LINUX', True)
    monkeypatch.setattr(module.proton, 'wrap_command', lambda command, **_: command)
    command, _ = module.get_start_command(server)
    assert '-noconsole' in command and '-console' not in command


def test_process_launch_uses_prepared_wine_prefix_instead_of_empty_proton_prefix(server, tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(module, 'IS_LINUX', True)
    monkeypatch.setattr(module, 'sync_server_config', lambda _: None)
    monkeypatch.setattr(module, 'apply_automatic_mods', lambda _: None)
    monkeypatch.setattr(module.runtime_module, 'resolve_runtime_metadata', lambda _: {'runtime': 'process'})
    monkeypatch.setattr(module.proton, 'find_wine', lambda: '/usr/bin/wine')
    monkeypatch.setattr(module.proton, 'prepare_wineprefix', lambda prefix: calls.append(prefix))
    module.prestart(server)
    assert calls == [str(tmp_path / '.alphagsm-wineprefix')]
    executable = tmp_path / 'DedicatedServer64/SpaceEngineersDedicated.exe'
    executable.parent.mkdir()
    executable.write_bytes(b'fixture')
    server.data['port'] = 27016
    monkeypatch.setattr(module.proton, 'wrap_command', lambda command, **kwargs: calls.append(kwargs) or command)
    module.get_start_command(server)
    assert calls[-1] == {'wineprefix': str(tmp_path / '.alphagsm-wineprefix'), 'prefer_proton': False}


def test_container_prestart_does_not_create_a_host_wine_prefix(server, monkeypatch):
    monkeypatch.setattr(module, 'IS_LINUX', True)
    monkeypatch.setattr(module, 'sync_server_config', lambda _: None)
    monkeypatch.setattr(module, 'apply_automatic_mods', lambda _: None)
    monkeypatch.setattr(module.runtime_module, 'resolve_runtime_metadata', lambda _: {'runtime': 'docker'})
    monkeypatch.setattr(module.proton, 'prepare_wineprefix', lambda _: pytest.fail('Container prepares its own prefix'))
    module.prestart(server)


@pytest.mark.parametrize("proton_available", [True, False])
def test_existing_proton_layout_uses_its_original_prefix(server, tmp_path, monkeypatch, proton_available):
    prefix = tmp_path / 'operator-compat'
    native_prefix = prefix / 'pfx'
    native_prefix.mkdir(parents=True)
    (native_prefix / 'system.reg').write_text('operator runtime registry')
    (prefix / 'version').write_text('operator Proton version')
    executable = tmp_path / 'DedicatedServer64/SpaceEngineersDedicated.exe'
    executable.parent.mkdir()
    executable.write_bytes(b'fixture')
    server.data.update(wineprefix=str(prefix), port=27016)
    monkeypatch.setattr(module, 'IS_LINUX', True)
    monkeypatch.setattr(module.proton, 'find_proton', lambda: '/opt/proton/proton' if proton_available else None)
    options = []
    monkeypatch.setattr(module.proton, 'wrap_command', lambda command, **kwargs: options.append(kwargs) or command)
    before = {path.relative_to(prefix): path.read_bytes() for path in prefix.rglob('*') if path.is_file()}
    module.get_start_command(server)
    assert options == [{'wineprefix': str(prefix if proton_available else native_prefix),
                        'prefer_proton': proton_available}]
    assert {path.relative_to(prefix): path.read_bytes() for path in prefix.rglob('*') if path.is_file()} == before
    assert not (prefix / 'system.reg').exists()


@pytest.mark.parametrize("desired", [["456"], []])
def test_running_server_refuses_apply_and_cleanup_before_io(server, tmp_path, monkeypatch, desired):
    ws = adapter()
    ws.apply_workshop(server, ["123"])
    before_files = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    before_state, before_saves = deepcopy(server.data), server.data.saved
    monkeypatch.setattr(ws.runtime_module, "check_server_running", lambda _: True)
    monkeypatch.setattr(ws, "read_xml", lambda *_: pytest.fail("Running guard must precede native XML access"))
    with pytest.raises(ServerError, match="Stop.*running"):
        ws.apply_workshop(server, desired)
    assert {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before_files
    assert server.data == before_state and server.data.saved == before_saves
