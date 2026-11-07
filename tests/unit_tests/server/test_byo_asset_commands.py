"""Asset CLI routing for game-specific guidance and explicit acquisition."""
import json
from types import SimpleNamespace

import pytest

from server import ServerError, runtime
from server.server import Server


def instance(tmp_path):
    from gamemodules import q3server
    server = Server.__new__(Server)
    server.name = "q3"
    server.data = {"dir": str(tmp_path / "server")}
    server.module = q3server
    return server


def test_requirements_prints_sources_without_install_or_auth(tmp_path,capsys):
    server=instance(tmp_path)
    server.assets("requirements",as_json=True)
    report=json.loads(capsys.readouterr().out)
    assert report['module']=='q3server'
    assert next(s for s in report['sources'] if s['kind']=='steamcmd')['app_id']==2200
    assert not (tmp_path/'server').exists()


def test_checks_include_file_sources_and_never_claim_game_readiness(tmp_path,capsys):
    server=instance(tmp_path)
    with pytest.raises(ServerError):
        server.assets('check',as_json=True)
    report=json.loads(capsys.readouterr().out)
    assert report['missing']==['baseq3/pak0.pk3']
    assert report['sources']
    assert report['game_readiness']=='not-checked'


def test_fetch_is_stopped_only_and_forwards_profile(tmp_path,monkeypatch):
    from server import assets
    server=instance(tmp_path)
    monkeypatch.setattr(runtime,'get_runtime',lambda _s:SimpleNamespace(is_running=lambda _s:True))
    with pytest.raises(ServerError,match='stopped'):
        server.assets('fetch','steam-owned',auth_profile='private')
    monkeypatch.setattr(runtime,'get_runtime',lambda _s:SimpleNamespace(is_running=lambda _s:False))
    calls=[]
    monkeypatch.setattr(assets.byo_acquire,'acquire',lambda *a,**k:calls.append((a,k)) or {'status':'ready'})
    server.assets('fetch','steam-owned',auth_profile='private')
    assert calls[0][0][2]=='steam-owned'
    assert calls[0][1]=={'auth_profile':'private'}


def test_manual_game_import_cannot_bypass_distribution_or_secret_checks(tmp_path,monkeypatch):
    from gamemodules import dstserver
    server=instance(tmp_path)
    server.module=dstserver
    monkeypatch.setattr(runtime,'get_runtime',lambda _s:SimpleNamespace(is_running=lambda _s:False))
    with pytest.raises(ServerError,match='(?i)manual'):
        server.assets('import',str(tmp_path))


def test_auth_profile_option_is_not_silently_ignored_on_other_actions(tmp_path):
    with pytest.raises(ServerError,match='fetch'):
        instance(tmp_path).assets('requirements',auth_profile='private')


@pytest.mark.parametrize('arguments,expected_args,expected_options', [
    (['requirements', '--json'], ['requirements'], {'as_json': True}),
    (['fetch', 'steam-owned', '--auth-profile', 'owned'], ['fetch', 'steam-owned'], {'auth_profile': 'owned'}),
    (['export', '/source', '--output', '/output.zip'], ['export', '/source'], {'output': '/output.zip'}),
])
def test_real_assets_option_spec_parses(arguments, expected_args, expected_options):
    from utils.cmdparse import cmdparse
    assert cmdparse.parse(arguments, Server.default_command_args['assets']) == (expected_args, expected_options)


def test_setup_asset_source_option_has_a_valid_shortform_sequence():
    from utils.cmdparse import cmdparse
    assert cmdparse.parse(['--assets', '/source'], Server.default_command_args['setup']) == ([], {'assets_source': '/source'})


@pytest.mark.parametrize('module_id', ['ets2server', 'atsserver'])
@pytest.mark.parametrize('contents', [None, b'', b'client export'])
def test_absolute_truck_home_requirements_and_check(tmp_path, capsys, module_id, contents):
    import importlib
    server = instance(tmp_path)
    server.module = importlib.import_module('gamemodules.' + module_id)
    home = tmp_path / 'external-home'
    server.data['configdir'] = str(home)
    if contents is not None:
        home.mkdir()
        for name in ('server_packages.sii', 'server_packages.dat'):
            (home / name).write_bytes(contents)

    server.assets('requirements', as_json=True)
    recipe = json.loads(capsys.readouterr().out)
    expected = ['server_packages.sii', 'server_packages.dat']
    assert [item['path'] for item in recipe['requirements']] == expected
    assert recipe['root_setting'] == 'configdir'
    assert recipe['target'] == ''
    assert recipe['managed_import'] is False
    assert 'manual staging' in recipe['manual_reason']
    assert all(name in recipe['manual_reason'] for name in expected)
    if contents:
        server.assets('check', as_json=True)
    else:
        with pytest.raises(ServerError, match='Required assets are missing'):
            server.assets('check', as_json=True)
    report = json.loads(capsys.readouterr().out)
    assert report['ready'] is bool(contents)
    assert report['missing'] == ([] if contents else expected)
    assert report['game_readiness'] == 'not-checked'
    assert not (tmp_path / 'server').exists()


@pytest.mark.parametrize('module_id', ['ets2server', 'atsserver'])
@pytest.mark.parametrize('action', ['import', 'export'])
def test_absolute_truck_home_managed_operations_are_read_only(
        tmp_path, monkeypatch, module_id, action):
    import importlib
    server = instance(tmp_path)
    server.module = importlib.import_module('gamemodules.' + module_id)
    home = tmp_path / 'external-home'
    home.mkdir()
    server.data['configdir'] = str(home)
    before = {'server_packages.sii': b'original sii', 'server_packages.dat': b'original dat'}
    for name, payload in before.items():
        (home / name).write_bytes(payload)
    monkeypatch.setattr(runtime, 'get_runtime', lambda _s: SimpleNamespace(is_running=lambda _s: False))
    options = {'output': str(tmp_path / 'exports.zip')} if action == 'export' else {}

    with pytest.raises(ServerError, match='manual staging'):
        server.assets(action, str(home), **options)

    assert {path.name: path.read_bytes() for path in home.iterdir()} == before
    assert not (tmp_path / 'exports.zip').exists()
    assert not (tmp_path / 'server').exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ['external-home']


@pytest.mark.parametrize('module_id', ['ets2server', 'atsserver'])
def test_relative_truck_home_retains_import_export_and_ownership(
        tmp_path, monkeypatch, capsys, module_id):
    import importlib
    import zipfile
    server = instance(tmp_path)
    server.module = importlib.import_module('gamemodules.' + module_id)
    server.data['configdir'] = 'custom-home'
    source = tmp_path / 'client-export'
    source.mkdir()
    filenames = ['server_packages.dat', 'server_packages.sii']
    for name in filenames:
        (source / name).write_bytes(('owned ' + name).encode())
    monkeypatch.setattr(runtime, 'get_runtime', lambda _s: SimpleNamespace(is_running=lambda _s: False))

    server.assets('import', str(source), as_json=True)
    report = json.loads(capsys.readouterr().out)
    expected = ['custom-home/' + name for name in filenames]
    assert sorted(report['copied']) == expected
    manifest = json.loads((tmp_path / 'server/.alphagsm/assets.json').read_text())
    assert sorted(manifest['files']) == expected
    assert not (tmp_path / 'server/custom-home/.alphagsm').exists()
    server.assets('check', as_json=True)
    assert json.loads(capsys.readouterr().out)['ready']
    output = tmp_path / 'exports.zip'
    server.assets('export', str(source), output=str(output), as_json=True)
    assert sorted(json.loads(capsys.readouterr().out)['files']) == filenames
    with zipfile.ZipFile(output) as bundle:
        assert sorted(bundle.namelist()) == filenames
        for name in filenames:
            assert bundle.read(name) == (source / name).read_bytes()
            assert (tmp_path / 'server/custom-home' / name).read_bytes() == bundle.read(name)
