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
