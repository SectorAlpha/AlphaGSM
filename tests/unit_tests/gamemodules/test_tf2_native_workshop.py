"""TF2 Workshop maps activate through native commands without account keys."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from gamemodules import teamfortress2 as module
from server import ServerError
from server.modsupport import workshop


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
    assert not any('steamaccount' in value or 'authkey' in value for value in command)
    cache=Path(server.data['dir'])/'steamapps/workshop/content/440/123/map.bsp'
    cache.parent.mkdir(parents=True); cache.write_bytes(b'engine cached map')
    mod(server,'cleanup')
    assert not cfg.exists() and cache.exists()
    command,_=module.get_start_command(server)
    assert 'alphagsm_workshop.cfg' not in command


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
