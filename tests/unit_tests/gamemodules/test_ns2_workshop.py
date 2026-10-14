"""Native NS2 Workshop mod IDs and map-cycle ownership."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gamemodules import ns2server as module
from server import ServerError
from server.modsupport import workshop


class Data(dict):
    def save(self):
        pass


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    server=SimpleNamespace(name='ns2-native',data=Data())
    module.configure(server,False,27015,str(tmp_path))
    exe=tmp_path/'x64/server_linux'; exe.parent.mkdir(); exe.write_bytes(b'engine')
    def details(method, ids, key):
        del key
        if method=='GetCollectionDetails':
            return {str(item):{'result':1,'children':[{'publishedfileid':'123'},{'publishedfileid':'124'}]} for item in ids}
        return {str(item):{'result':1,'consumer_app_id':4920,'file_type':2 if str(item)=='900' else 0} for item in ids}
    monkeypatch.setattr(workshop,'_post_details',details)
    return server


def cycle(server):
    return Path(server.data['dir'])/server.name/'MapCycle.json'


def test_native_hex_startup_and_cycle_merge_keep_operator_settings(adapter):
    server=adapter; path=cycle(server); path.parent.mkdir(); path.write_text(json.dumps({'mods':['abc'], 'maps':['ns2_summit'], 'mode':'random','time':45}))
    mod=module.command_functions['mod']
    mod(server,'add','workshop','https://steamcommunity.com/sharedfiles/filedetails/?id=123')
    mod(server,'add','workshop-collection','900'); mod(server,'apply')
    assert json.loads(path.read_text())=={'mods':['abc','7b','7c'],'maps':['ns2_summit'],'mode':'random','time':45}
    command,_=module.get_start_command(server)
    assert command[command.index('-mods')+1]=='abc 7b 7c'
    assert module.workshop_app_id==4920
    mod(server,'cleanup')
    assert json.loads(path.read_text())=={'mods':['abc'],'maps':['ns2_summit'],'mode':'random','time':45}
    command,_=module.get_start_command(server)
    assert command[command.index('-mods')+1]=='abc'


def test_external_ids_and_modified_owned_id_survive_cleanup(adapter):
    server=adapter; mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply')
    path=cycle(server); data=json.loads(path.read_text()); data['mods']=['7B','def']; data['time']=71; path.write_text(json.dumps(data))
    mod(server,'cleanup')
    remaining=json.loads(path.read_text()); assert remaining['mods']==['7B','def'] and remaining['time']==71


def test_reject_wrong_game_invalid_cycle_and_symlink_without_writes(adapter, monkeypatch, tmp_path):
    server=adapter; mod=module.command_functions['mod']
    monkeypatch.setattr(workshop,'_post_details',lambda method,ids,key:{str(item):{'result':1,'consumer_app_id':550,'file_type':0} for item in ids})
    with pytest.raises(ServerError,match='belongs'): mod(server,'add','workshop','123')
    assert not cycle(server).exists()
    server.data['mods']['desired']['workshop']=[{'workshop_id':'123'}]
    monkeypatch.setattr(workshop,'_post_details',lambda method,ids,key:{str(item):{'result':1,'consumer_app_id':4920,'file_type':0} for item in ids})
    outside=tmp_path/'outside'; outside.mkdir(); (tmp_path/server.name).symlink_to(outside)
    with pytest.raises(ServerError,match='symlink'): mod(server,'apply')
    assert not list(outside.iterdir())


def test_prestart_updates_native_cycle_and_autoapply_false_preserves_file(adapter):
    server=adapter; mod=module.command_functions['mod']; mod(server,'add','workshop','123'); module.prestart(server)
    path=cycle(server); original=path.read_bytes(); assert json.loads(original)['mods']==['7b']
    server.data['mods']['autoapply']=False; mod(server,'add','workshop','124'); module.prestart(server)
    assert path.read_bytes()==original


def test_invalid_native_ids_and_duplicate_json_fields_fail_atomically(adapter):
    server=adapter; path=cycle(server); path.parent.mkdir(); path.write_text('{"mods":["bad;quit"],"maps":["ns2_summit"]}')
    original=path.read_bytes(); mod=module.command_functions['mod']; mod(server,'add','workshop','123')
    with pytest.raises(ServerError): mod(server,'apply')
    assert path.read_bytes()==original
    path.write_text('{"mods":[],"mods":["abc"]}')
    original=path.read_bytes()
    with pytest.raises(ServerError): mod(server,'apply')
    assert path.read_bytes()==original


def test_disabled_autoapply_cannot_write_server_directories_through_symlinks(adapter, tmp_path):
    server=adapter; server.data['mods']['autoapply']=False
    outside=tmp_path/'outside'; outside.mkdir(); (tmp_path/server.name).symlink_to(outside)
    with pytest.raises(ServerError,match='symlink'): module.prestart(server)
    assert not list(outside.iterdir())


def test_engine_map_origin_requires_exact_map_and_workshop_id():
    from tests.smoke_tests.ns2_workshop import assert_map_origin
    assert_map_origin([{'name':'ns2_Jambi','modId':129599221}],'ns2_jambi','129599221')
    assert_map_origin([{'name':'ns2_Jambi','modId':'7b986f5'}],'ns2_jambi','129599221')
    for payload in ([{'name':'ns2_summit','modId':129599221}], [{'name':'ns2_Jambi','modId':1295992210}], [{'name':'ns2_Jambi','modId':False}], {'mods':['7b986f5']}):
        with pytest.raises(AssertionError): assert_map_origin(payload,'ns2_jambi','129599221')


def test_native_spark_parser_receives_quoted_hyphen_values_and_local_mod_binding(adapter):
    command,_=module.get_start_command(adapter)
    assert command[command.index('-config_path')+1]=='"./ns2-native"'
    assert command[command.index('-modstorage')+1]=='"./ns2-native/Workshop"'
    assert command[command.index('-name')+1]=='AlphaGSM ns2-native'  # Spark quotes whitespace itself.
    assert '-modserveraddress' not in command
    adapter.data['modserveraddress']='127.0.0.1'
    command,_=module.get_start_command(adapter)
    assert command[command.index('-modserveraddress')+1]=='127.0.0.1'


def test_cleanup_of_deleted_native_config_releases_owner_without_recreating_it(adapter):
    mod=module.command_functions['mod']; mod(adapter,'add','workshop','123'); mod(adapter,'apply')
    path=cycle(adapter); path.unlink(); mod(adapter,'cleanup')
    assert not path.exists() and 'ns2_workshop' not in adapter.data


def test_native_web_admin_map_change_rejects_console_injection_before_request(monkeypatch):
    from tests.smoke_tests import ns2_workshop
    monkeypatch.setattr(ns2_workshop, '_request_engine', lambda *args: pytest.fail('unsafe map reached native API'))
    with pytest.raises(ValueError): ns2_workshop.change_map('127.0.0.1',8080,'admin','private','ns2_jambi;quit')


def test_web_admin_binding_is_explicit_and_survives_container_launch(adapter):
    command, _ = module.get_start_command(adapter)
    assert '-webdomain' not in command
    adapter.data['webdomain'] = module.checkvalue(adapter, ['webdomain'], '0.0.0.0')
    command, _ = module.get_start_command(adapter)
    assert command[command.index('-webdomain') + 1] == '0.0.0.0'
    spec = module.get_container_spec(adapter)
    assert spec['command'][spec['command'].index('-webdomain') + 1] == '0.0.0.0'
