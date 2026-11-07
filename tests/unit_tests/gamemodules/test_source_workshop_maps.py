"""Dedicated Source Workshop maps need real game assets and safe ownership."""

import importlib
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport import workshop


class Data(dict):
    def save(self):
        pass


def bsp():
    return struct.pack('<4si', b'VBSP', 20) + b'\0' * 1028


@pytest.fixture(params=[('nmrihserver',224260,'nmrih','nmo_fixture'), ('bb2server',346330,'brainbread2','bbc_fixture')])
def adapter(request, tmp_path, monkeypatch):
    name, app_id, game_dir, map_name = request.param
    module = importlib.import_module(f'gamemodules.{name}')
    server = SimpleNamespace(name=f'workshop-{name}', data=Data(), module=module)
    module.configure(server, ask=False, port=27015, dir=str(tmp_path))
    def details(method, ids, key):
        del key
        if method == 'GetCollectionDetails':
            return {str(item): {'result':1,'children':[{'publishedfileid':'123'},{'publishedfileid':'124'}]} for item in ids}
        return {str(item): {'result':1,'consumer_app_id':app_id,'file_type':2 if str(item)=='900' else 0} for item in ids}
    monkeypatch.setattr(workshop, '_post_details', details)
    payloads = {}
    for item, suffix in [('123',''),('124','_second')]:
        root=tmp_path/'.alphagsm/workshop/content'/str(app_id)/item
        (root/'maps').mkdir(parents=True)
        (root/'maps'/f'{map_name}{suffix}.bsp').write_bytes(bsp())
        payloads[item]=root
    return module, server, app_id, game_dir, map_name, payloads


def install_downloader(adapter, monkeypatch):
    module, _, _, _, _, payloads = adapter
    implementation=importlib.import_module(f'{module.__name__}.workshop')
    monkeypatch.setattr(implementation,'download_workshop_items',lambda server, app, ids: {item:payloads[item] for item in ids})


def native_root(adapter, item='123'):
    module, server, app_id, game_dir, _, _ = adapter
    root = Path(server.data['dir']) / game_dir
    if module.__name__.endswith('bb2server'):
        return root / 'workshop/content' / str(app_id) / item
    return root


def test_item_url_collection_publish_native_maps_and_cleanup_only_owned(adapter, monkeypatch):
    module, server, app_id, game_dir, map_name, _ = adapter
    install_downloader(adapter, monkeypatch)
    mod=module.command_functions['mod']
    mod(server,'add','workshop','https://steamcommunity.com/sharedfiles/filedetails/?id=123')
    mod(server,'add','workshop-collection','900')
    mod(server,'apply')
    assert module.workshop_app_id == app_id
    game=native_root(adapter)
    assert (game/'maps'/f'{map_name}.bsp').read_bytes()==bsp()
    assert (native_root(adapter,'124')/'maps'/f'{map_name}_second.bsp').is_file()
    (game/'maps/operator.bsp').write_bytes(bsp())
    mod(server,'cleanup')
    assert not (game/'maps'/f'{map_name}.bsp').exists()
    assert (game/'maps/operator.bsp').is_file()


@pytest.mark.parametrize('invalid',['header','family','client','symlink'])
def test_reject_invalid_map_family_client_only_and_unsafe_payload_before_publication(adapter, monkeypatch, invalid):
    module, server, _, game_dir, map_name, payloads = adapter
    install_downloader(adapter, monkeypatch)
    root=payloads['123']
    path=root/'maps'/f'{map_name}.bsp'
    if invalid=='header': path.write_bytes(b'garbage')
    elif invalid=='family': path.rename(path.with_name('de_dust2.bsp'))
    elif invalid=='client': path.unlink(); (root/'materials').mkdir(); (root/'materials/client.vtf').write_bytes(b'client')
    else: path.unlink(); path.symlink_to(root.parent/'124/maps'/f'{map_name}_second.bsp')
    module.command_functions['mod'](server,'add','workshop','123')
    with pytest.raises(ServerError): module.command_functions['mod'](server,'apply')
    assert not (native_root(adapter)/'maps'/f'{map_name}.bsp').exists()


def test_unowned_collision_and_external_edits_are_preserved(adapter, monkeypatch):
    module, server, _, game_dir, map_name, _ = adapter
    install_downloader(adapter, monkeypatch)
    mod=module.command_functions['mod']
    mod(server,'add','workshop','123')
    path=native_root(adapter)/'maps'/f'{map_name}.bsp'
    path.parent.mkdir(parents=True)
    path.write_bytes(b'operator')
    with pytest.raises(ServerError,match='unowned'): mod(server,'apply')
    assert path.read_bytes()==b'operator'
    path.unlink(); mod(server,'apply')
    path.write_bytes(b'edited')
    with pytest.raises(ServerError,match='modified'): mod(server,'cleanup')
    assert path.read_bytes()==b'edited'
    assert [entry['workshop_id'] for entry in server.data['mods']['desired']['workshop']] == ['123']


def test_wrong_game_rejected_and_prestart_retains_addons(adapter, monkeypatch):
    module, server, _, game_dir, map_name, _ = adapter
    install_downloader(adapter, monkeypatch)
    mod=module.command_functions['mod']
    mod(server,'add','workshop','123')
    calls=[]
    monkeypatch.setattr(module.MODULE,'prestart',lambda instance:calls.append('valve'))
    monkeypatch.setattr(module.MOD_SUPPORT,'apply_configured_mods',lambda instance:calls.append('addons'))
    module.prestart(server)
    assert calls==['valve','addons']
    assert (native_root(adapter)/'maps'/f'{map_name}.bsp').exists()
    server.data['mods']['autoapply']=False
    calls.clear(); module.prestart(server); assert calls==['valve']
    monkeypatch.setattr(workshop,'_post_details',lambda method, ids, key:{str(item):{'result':1,'consumer_app_id':550,'file_type':0} for item in ids})
    with pytest.raises(ServerError,match='belongs'): mod(server,'add','workshop','124')


def test_native_map_sidecars_keep_runtime_color_correction_and_ignore_editor_sources(adapter, monkeypatch):
    module, server, _, game_dir, _, payloads = adapter
    install_downloader(adapter, monkeypatch)
    root=payloads['123']
    (root/'materials').mkdir(); (root/'materials/color.raw').write_bytes(b'color correction')
    (root/'models').mkdir(); (root/'models/editor.smd').write_bytes(b'editor only')
    mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply')
    game=native_root(adapter)
    assert (game/'materials/color.raw').read_bytes()==b'color correction'
    assert not (game/'models/editor.smd').exists()


def test_bare_bsp_and_truncated_lump_bounds(adapter, monkeypatch):
    module, server, _, game_dir, map_name, payloads = adapter
    install_downloader(adapter, monkeypatch)
    root=payloads['123']; path=root/'maps'/f'{map_name}.bsp'
    flat=root/path.name; path.rename(flat)
    mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply')
    assert (native_root(adapter)/'maps'/flat.name).is_file()
    invalid=bytearray(bsp()); struct.pack_into('<ii',invalid,8,1036,100)
    flat.write_bytes(invalid)
    with pytest.raises(ServerError,match='lump'): mod(server,'apply')
    assert (native_root(adapter)/'maps'/flat.name).read_bytes()==bsp()


def test_entire_collection_is_preflighted_before_publishing_any_map(adapter, monkeypatch):
    module, server, _, game_dir, map_name, payloads = adapter
    install_downloader(adapter, monkeypatch)
    (payloads['124']/'maps'/f'{map_name}_second.bsp').write_bytes(b'invalid second map')
    mod=module.command_functions['mod']; mod(server,'add','workshop-collection','900')
    with pytest.raises(ServerError): mod(server,'apply')
    assert not (native_root(adapter)/'maps').exists()


@pytest.mark.parametrize('adapter', [('bb2server',346330,'brainbread2','bbc_fixture')], indirect=True)
def test_bb2_map_setting_accepts_installed_native_workshop_map_and_rejects_unknown(adapter, monkeypatch):
    module, server, _, game_dir, map_name, _ = adapter
    install_downloader(adapter, monkeypatch)
    base=Path(server.data['dir'])/game_dir/'maps'; base.mkdir(parents=True)
    (base/'bba_barracks.bsp').write_bytes(bsp())
    mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply')
    assert module.checkvalue(server,['map'],map_name)==map_name
    assert module.checkvalue(server,['startmap'],map_name)==map_name
    assert module.checkvalue(server,['map'],'bba_barracks')=='bba_barracks'
    with pytest.raises(ServerError): module.checkvalue(server,['map'],'bbc_missing')
    foreign=Path(server.data['dir'])/'unrelated/maps/bbc_foreign.bsp'
    foreign.parent.mkdir(parents=True); foreign.write_bytes(bsp())
    server.data['mods']['owned_payloads']['bb2server_workshop_maps']['unrelated/maps/bbc_foreign.bsp']='0'*64
    with pytest.raises(ServerError): module.checkvalue(server,['map'],'bbc_foreign')


@pytest.mark.parametrize('adapter', [('nmrihserver',224260,'nmrih','nmo_fixture')], indirect=True)
def test_nmrih_objective_sidecar_is_native_server_content(adapter, monkeypatch):
    module, _, _, _, map_name, payloads = adapter
    install_downloader(adapter, monkeypatch)
    (payloads['123']/'maps'/f'{map_name}.nmo').write_bytes(b'objective metadata')
    mod=module.command_functions['mod']; mod(adapter[1],'add','workshop','123'); mod(adapter[1],'apply')
    assert (native_root(adapter)/'maps'/f'{map_name}.nmo').read_bytes()==b'objective metadata'
