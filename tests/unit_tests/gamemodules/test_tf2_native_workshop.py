"""TF2 Workshop maps activate through native commands without account keys."""

import importlib.util
import json
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import pytest

from gamemodules import teamfortress2 as module
from server import ServerError
from server.modsupport import workshop
from server import runtime as runtime_module


class Data(dict):
    def save(self):
        pass


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    server=SimpleNamespace(name='tf2-workshop',data=Data())
    module.configure(server,False,27015,str(tmp_path))
    (tmp_path/'srcds_run').write_text('launcher')
    def details(method, ids, key):
        del key
        if method=='GetCollectionDetails':
            return {str(item):{'result':1,'children':[{'publishedfileid':'123'},{'publishedfileid':'124'}]} for item in ids}
        return {str(item):{'result':1,'consumer_app_id':440,'file_type':2 if str(item)=='900' else 0,
                          'tags':[{'tag':'Control Point'}]} for item in ids}
    monkeypatch.setattr(workshop,'_post_details',details)
    return server


def test_id_url_collection_native_sync_and_cleanup_preserve_engine_cache(adapter):
    server=adapter; mod=module.command_functions['mod']
    mod(server,'add','workshop','https://steamcommunity.com/sharedfiles/filedetails/?id=123')
    mod(server,'add','workshop-collection','900'); mod(server,'apply')
    cfg=Path(server.data['dir'])/'tf/cfg/alphagsm_workshop.cfg'
    assert cfg.read_text()=='tf_workshop_map_sync 123\ntf_workshop_map_sync 124\n'
    command,_=module.get_start_command(server)
    assert ['+exec','alphagsm_workshop.cfg']==command[-2:]
    assert command[command.index('-ugcpath') + 1] == str(Path(server.data['dir']) / 'steamapps/workshop')
    spec = module.get_container_spec(server)
    native = shlex.split(spec['command'][spec['command'].index('--command') + 1])
    assert native[native.index('-ugcpath') + 1] == '/srv/server/steamapps/workshop'
    assert str(Path(server.data['dir']) / 'steamapps/workshop') not in native
    assert spec['run_as_host_user'] and spec['container_home'] == '/home/alphagsm'
    assert spec['init'] is True
    assert spec['env']['HOME'] == '/home/alphagsm'
    requirements = module.get_runtime_requirements(server)
    assert requirements['run_as_host_user'] and requirements['env']['HOME'] == '/home/alphagsm'
    assert requirements['init'] is True
    assert any(mount['target'] == '/home/alphagsm' and mount['mode'] == 'rw' for mount in spec['mounts'])
    assert not any('steamaccount' in value or 'authkey' in value for value in command)
    cache=Path(server.data['dir'])/'steamapps/workshop/content/440/123/map.bsp'
    cache.parent.mkdir(parents=True); cache.write_bytes(b'engine cached map')
    mod(server,'cleanup')
    assert not cfg.exists() and cache.exists()
    command,_=module.get_start_command(server)
    assert 'alphagsm_workshop.cfg' not in command
    assert '-ugcpath' not in command


def test_native_map_config_rejects_operator_collision_and_external_edits(adapter):
    server=adapter; mod=module.command_functions['mod']
    mod(server,'add','workshop','123')
    cfg=Path(server.data['dir'])/'tf/cfg/alphagsm_workshop.cfg'
    cfg.parent.mkdir(parents=True); cfg.write_text('// operator configuration\n')
    with pytest.raises(ServerError,match='unowned'): mod(server,'apply')
    assert cfg.read_text()=='// operator configuration\n'
    cfg.unlink(); mod(server,'apply'); cfg.write_text('// operator changed configuration\n')
    with pytest.raises(ServerError,match='modified'): mod(server,'cleanup')
    assert cfg.read_text()=='// operator changed configuration\n'


def test_container_library_maps_dedicated_and_native_workshop_consumer_apps(adapter):
    adapter.module = module
    spec = dict(module.get_container_spec(adapter), runtime_family='steamcmd-linux')
    library = runtime_module._steam_runtime_library_state(adapter, spec, 'runtime/tf2/home')
    assert '"path" "/srv/server"' in library['content']
    assert '"232250" "0"' in library['content']
    assert '"440" "0"' in library['content']
    assert 'appworkshop' not in library['relative_file']


def test_wrong_game_and_cosmetics_cannot_activate_as_maps(adapter, monkeypatch):
    server=adapter; mod=module.command_functions['mod']
    monkeypatch.setattr(workshop,'_post_details',lambda method,ids,key:{str(item):{'result':1,'consumer_app_id':550,'file_type':0} for item in ids})
    with pytest.raises(ServerError,match='belongs'): mod(server,'add','workshop','123')
    monkeypatch.setattr(workshop,'_post_details',lambda method,ids,key:{str(item):{'result':1,'consumer_app_id':440,'file_type':0,'tags':[{'tag':'Cosmetics'}]} for item in ids})
    mod(server,'add','workshop','123')
    with pytest.raises(ServerError,match='map'): mod(server,'apply')
    assert not (Path(server.data['dir'])/'tf/cfg/alphagsm_workshop.cfg').exists()


def test_workshop_startmap_requires_a_valid_desired_native_id(adapter):
    server=adapter; mod=module.command_functions['mod']; mod(server,'add','workshop','123')
    assert module.checkvalue(server,['map'],'workshop/123')=='workshop/123'
    with pytest.raises(ServerError): module.checkvalue(server,['map'],'workshop/124')
    with pytest.raises(ServerError): module.checkvalue(server,['map'],'workshop/123;quit')


def test_prestart_reconciles_native_maps_even_when_steamclient_link_already_matches(adapter, monkeypatch, tmp_path):
    server=adapter; mod=module.command_functions['mod']; mod(server,'add','workshop','123')
    tool=tmp_path/'steamcmd'; source=tool/'linux64/steamclient.so'
    source.parent.mkdir(parents=True); source.write_bytes(b'sdk')
    destination=tmp_path/'sdk64/steamclient.so'; destination.parent.mkdir(); destination.symlink_to(source)
    monkeypatch.setattr(module,'STEAMCLIENT_DST',str(destination))
    from gamemodules.teamfortress2 import main
    monkeypatch.setattr(main.steamcmd,'STEAMCMD_DIR',str(tool))
    module.prestart(server)
    cfg=Path(server.data['dir'])/'tf/cfg/alphagsm_workshop.cfg'
    assert cfg.read_text()=='tf_workshop_map_sync 123\n'


def test_native_map_probe_requires_ready_exact_id_and_actual_current_canonical_map():
    from tests.smoke_tests.tf2_workshop import assert_native_map, assert_native_ready
    frame = ('BEGIN-fresh\nFileID Map Name Status\n'
             '454299390 workshop/cp_orange_x3.ugc454299390 ready\n'
             'map     : workshop/cp_orange_x3.ugc454299390 at: 0 x, 0 y, 0 z\n'
             'END-fresh\n')
    assert assert_native_map(frame, '454299390', 'cp_orange_x3', 'fresh') == 'workshop/cp_orange_x3.ugc454299390'
    stock = frame.replace('map     : workshop/cp_orange_x3.ugc454299390', 'map     : cp_dustbowl')
    assert assert_native_ready(stock, '454299390', 'cp_orange_x3', 'fresh') == 'workshop/cp_orange_x3.ugc454299390'
    with pytest.raises(AssertionError):
        assert_native_map(stock, '454299390', 'cp_orange_x3', 'fresh')
    with pytest.raises(AssertionError):
        assert_native_ready(frame.replace('ready', 'downloading'), '454299390', 'cp_orange_x3', 'fresh')
    for text in (frame.replace('ready', 'downloading'),
                 frame.replace('454299390', '4542993900'),
                 frame.replace('map     : workshop/cp_orange_x3.ugc454299390', 'map     : cp_dustbowl'),
                 frame.replace('map     : workshop/cp_orange_x3.ugc454299390', 'map     : cp_orange_x3'),
                 frame.replace('map     : workshop/cp_orange_x3.ugc454299390', 'map     : workshop/454299390'),
                 frame.replace('END-fresh', 'END-stale'),
                 frame.replace('BEGIN-fresh', 'BEGIN-stale'),
                 frame.replace('cp_orange_x3', 'cp_other'),
                 frame + frame.removesuffix('END-fresh\n'),
                 frame + frame.replace('map     : workshop/cp_orange_x3.ugc454299390', 'map     : cp_dustbowl')):
        with pytest.raises(AssertionError):
            assert_native_map(text, '454299390', 'cp_orange_x3', 'fresh')


@pytest.mark.parametrize('advertised_map', ['cp_orange_x3', 'workshop/454299390'])
@pytest.mark.parametrize('pending_frames', [0, 2])
@pytest.mark.parametrize('pending_map_frames', [0, 2])
@pytest.mark.parametrize('rotate_tokens', [False, True])
def test_workshop_lifecycle_requires_execution_instead_of_pending_a2s_map(
        monkeypatch, advertised_map, pending_frames, pending_map_frames, rotate_tokens):
    from tests.integration_tests import conftest as helpers
    monkeypatch.setitem(sys.modules, 'conftest', helpers)
    path = Path(__file__).resolve().parents[2] / 'integration_tests/test_tf2.py'
    spec = importlib.util.spec_from_file_location('_tf2_native_execution', path)
    lifecycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lifecycle)
    monkeypatch.setenv('ALPHAGSM_TF2_WORKSHOP_LOAD_ITEM', '454299390')
    monkeypatch.setenv('ALPHAGSM_TF2_WORKSHOP_MAP', 'cp_orange_x3')
    ticks = iter([*range(12), 601])
    monkeypatch.setattr(lifecycle, 'time', SimpleNamespace(monotonic=lambda: next(ticks), sleep=lambda _: None))
    commands = []
    token_ids = iter(f'fresh{index}' for index in range(20))
    monkeypatch.setattr(lifecycle, 'uuid', SimpleNamespace(
        uuid4=lambda: SimpleNamespace(hex=next(token_ids) if rotate_tokens else 'fresh')))
    frame = ('BEGIN-AlphaGSM-TF2-fresh\n'
             '454299390 workshop/cp_orange_x3.ugc454299390 ready\n'
             'map : workshop/cp_orange_x3.ugc454299390 at: 0 x, 0 y, 0 z\n'
             'END-AlphaGSM-TF2-fresh\n')

    def command(_env, _server, action, *args):
        commands.append((action, args))
        probe = next((arguments[0] for name, arguments in reversed(commands)
                      if name == 'send' and arguments[0].startswith('echo BEGIN-')), '')
        token = probe.split('BEGIN-', 1)[1].split(';', 1)[0] if probe else 'AlphaGSM-TF2-fresh'
        log_reads = sum(action == 'logs' for action, _args in commands)
        changed = ('send', ('changelevel workshop/454299390',)) in commands
        if action == 'logs' and log_reads <= pending_frames:
            # Download in progress must not enter blocking changelevel. Every
            # attempt needs a new complete native frame reporting ready.
            text = frame.removesuffix('END-AlphaGSM-TF2-fresh\n') if log_reads == 1 else frame.replace(
                'ready', 'downloading')
        elif action == 'logs' and changed and log_reads - pending_frames - 1 <= pending_map_frames:
            # A ready download does not prove the map switch has finished.
            text = frame.replace('map : workshop/cp_orange_x3.ugc454299390', 'map : cp_dustbowl')
        else:
            text = frame
        return SimpleNamespace(returncode=0, stdout=text.replace('AlphaGSM-TF2-fresh', token), stderr='')

    def info(*_args, **_kwargs):
        commands.append(('info', ('--json',)))
        return SimpleNamespace(returncode=0, stderr='', stdout=json.dumps(
            {'protocol': 'a2s', 'port': 27015, 'map': advertised_map}))

    monkeypatch.setattr(lifecycle, 'run_and_assert_ok', command)
    monkeypatch.setattr(lifecycle, 'run_alphagsm', info)
    if advertised_map.startswith('workshop/'):
        with pytest.raises(pytest.fail.Exception, match='execution evidence missing'):
            lifecycle._verify_native_workshop_map({}, 'tf2', ['454299390'], 27015)
    else:
        assert lifecycle._verify_native_workshop_map({}, 'tf2', ['454299390'], 27015) == advertised_map
    assert commands[0] == ('send', ('tf_workshop_map_sync 454299390',))
    change_index = commands.index(('send', ('changelevel workshop/454299390',)))
    assert sum(action == 'logs' for action, _args in commands[:change_index]) == pending_frames + 1
    assert all(action != 'info' for action, _args in commands[:change_index])
    assert commands[change_index + 1] == ('info', ('--json',))
    probes = [args for action, args in commands[change_index + 1:] if action == 'send']
    if advertised_map.startswith('workshop/'):
        assert not probes
    else:
        assert len(probes) == pending_map_frames + 1
        if rotate_tokens:
            all_probes = [args[0] for action, args in commands
                          if action == 'send' and args[0].startswith('echo BEGIN-')]
            assert len(set(all_probes)) == len(all_probes)
        else:
            assert probes == [('echo BEGIN-AlphaGSM-TF2-fresh; tf_workshop_map_status; status; echo END-AlphaGSM-TF2-fresh',)] * (pending_map_frames + 1)
