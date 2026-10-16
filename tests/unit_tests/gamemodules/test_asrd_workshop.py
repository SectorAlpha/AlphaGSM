"""Reactive Drop anonymous Windows runtime and native Workshop activation."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport import workshop


class Data(dict):
    def save(self):
        pass


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    module=importlib.import_module('gamemodules.asrdserver')
    server=SimpleNamespace(name='asrd-native',data=Data())
    module.configure(server,False,27015,str(tmp_path))
    (tmp_path/'srcds_console.exe').write_bytes(b'MZ fixture')
    def details(method, ids, key):
        del key
        if method=='GetCollectionDetails':
            return {str(item):{'result':1,'children':[{'publishedfileid':'123'},{'publishedfileid':'124'}]} for item in ids}
        return {str(item):{'result':1,'consumer_app_id':563560,'file_type':2 if str(item)=='900' else 0} for item in ids}
    monkeypatch.setattr(workshop,'_post_details',details)
    return module,server


def test_ids_urls_and_collection_use_native_workshop_cfg_preserving_operator_content(adapter):
    module,server=adapter; path=Path(server.data['dir'])/'reactivedrop/cfg/workshop.cfg'
    path.parent.mkdir(parents=True); path.write_text('// operator content\nrd_enable_workshop_item 777\n')
    mod=module.command_functions['mod']; mod(server,'add','workshop','https://steamcommunity.com/sharedfiles/filedetails/?id=123')
    mod(server,'add','workshop-collection','900'); mod(server,'apply')
    text=path.read_text(); assert 'rd_enable_workshop_item 123\nrd_enable_workshop_item 124\n' in text
    assert module.workshop_app_id==563560
    mod(server,'cleanup'); assert path.read_text()=='// operator content\nrd_enable_workshop_item 777\n'


def test_external_owned_block_edits_and_symlink_targets_fail_without_overwrite(adapter, tmp_path):
    module,server=adapter; mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply')
    path=Path(server.data['dir'])/'reactivedrop/cfg/workshop.cfg'
    path.write_text(path.read_text().replace('rd_enable_workshop_item 123','rd_enable_workshop_item 999'))
    changed=path.read_bytes()
    with pytest.raises(ServerError,match='modified|changed'): mod(server,'cleanup')
    assert path.read_bytes()==changed
    path.unlink(); path.symlink_to(tmp_path/'outside')
    with pytest.raises(ServerError,match='symlink'): mod(server,'apply')
    assert not (tmp_path/'outside').exists()


def test_wrong_game_rejected_and_created_config_cleanup_removes_only_owned_file(adapter, monkeypatch):
    module,server=adapter; mod=module.command_functions['mod']
    monkeypatch.setattr(workshop,'_post_details',lambda method,ids,key:{str(item):{'result':1,'consumer_app_id':550,'file_type':0} for item in ids})
    with pytest.raises(ServerError,match='belongs'): mod(server,'add','workshop','123')
    assert server.data['mods']['desired']['workshop']==[]


def test_install_downloads_game_and_sdk_anonymously_for_windows(adapter, monkeypatch):
    module,server=adapter; calls=[]
    monkeypatch.setattr(module.steamcmd,'download',lambda path,app,anonymous,**kwargs:calls.append((app,anonymous,kwargs)))
    module.doinstall(server)
    assert [row[:2] for row in calls]==[(1007,True),(563560,True)]
    assert all(row[2]['force_windows'] is True for row in calls)


def test_process_and_container_runtime_keep_native_source_ports_and_ssd_prefix(adapter, monkeypatch):
    module,server=adapter
    monkeypatch.setattr(module.proton,'wrap_command',lambda command,**kwargs:['wine',*command])
    command,directory=module.get_start_command(server)
    assert command[0]=='wine' and './srcds_console.exe' in command and 'reactivedrop' in command
    assert directory==server.data['dir'] and str(server.data['wineprefix']).startswith(server.data['dir'])
    requirements=module.get_runtime_requirements(server)
    assert requirements['family']=='wine-proton' and requirements['engine']=='docker'
    assert any(row['protocol']=='udp' and row['host']==27015 for row in requirements['ports'])


def test_native_engine_map_mapping_rejects_file_presence_and_prefix_ids():
    from tests.smoke_tests.asrd_workshop import native_map_owners
    assert native_map_owners('  maps/as_nest.bsp -> 848331447\n')=={'as_nest':'848331447'}
    assert native_map_owners('echo maps/as_nest.bsp -> 848331447\n/workshop/content/563560/848331447/as_nest.bsp\n')=={}


def test_created_workshop_config_cleanup_keeps_native_cache(adapter):
    module,server=adapter; root=Path(server.data['dir'])
    cache=root/'reactivedrop/workshop/848331447.vpk'; cache.parent.mkdir(parents=True); cache.write_bytes(b'engine managed')
    mod=module.command_functions['mod']; mod(server,'add','workshop','123'); mod(server,'apply'); mod(server,'cleanup')
    assert not (root/'reactivedrop/cfg/workshop.cfg').exists()
    assert cache.read_bytes()==b'engine managed'


def test_native_windows_launcher_executes_server_config_before_map_and_binds_explicit_ip(adapter, monkeypatch):
    module,server=adapter
    monkeypatch.setattr(module.proton,'wrap_command',lambda command,**kwargs:command)
    server.data['bindaddress']=module.checkvalue(server,'bindaddress','127.0.0.1')
    command,_=module.get_start_command(server)
    assert command[command.index('-ip')+1]=='127.0.0.1'
    assert command[command.index('+exec')+1]=='server.cfg'
    assert command.index('+exec') < command.index('+map')
    with pytest.raises(ServerError): module.checkvalue(server,'bindaddress','127.0.0.1;quit')


def test_update_stops_running_engine_before_download_config_and_mod_changes(adapter, monkeypatch):
    module,server=adapter; calls=[]
    server.isrunning=lambda:True
    server.stop=lambda:calls.append('stop')
    server.start=lambda:calls.append('start')
    monkeypatch.setattr(module,'doinstall',lambda *args,**kwargs:calls.append('download'))
    monkeypatch.setattr(module,'sync_server_config',lambda *args:calls.append('config'))
    monkeypatch.setattr(module,'_apply_automatic',lambda *args:calls.append('mods'))
    module.update(server,restart=True)
    assert calls==['stop','download','config','mods','start']


def test_failed_stop_prevents_all_update_mutations(adapter, monkeypatch):
    module,server=adapter
    server.isrunning=lambda:True
    def fail_stop(): raise ServerError('engine still running')
    server.stop=fail_stop
    monkeypatch.setattr(module,'doinstall',lambda *args,**kwargs:pytest.fail('download before stopped engine'))
    with pytest.raises(ServerError,match='still running'): module.update(server)


def test_sync_writes_selected_config_and_rejects_escape_before_any_write(adapter, tmp_path):
    module,server=adapter; root=Path(server.data['dir']); cfg=root/'reactivedrop/cfg'
    cfg.mkdir(parents=True); (cfg/'server.cfg').write_text('// operator default\n')
    (cfg/'custom.cfg').write_text('// custom operator setting\n')
    server.data['server_cfg']='custom.cfg'
    module.sync_server_config(server)
    assert (cfg/'server.cfg').read_text()=='// operator default\n'
    text=(cfg/'custom.cfg').read_text()
    assert '// custom operator setting' in text and 'sv_hibernate_when_empty 0' in text and 'rd_server_shutdown_when_empty 0' in text
    server.data['server_cfg']='../../../outside.cfg'
    with pytest.raises(ServerError): module.sync_server_config(server)
    assert not (root/'outside.cfg').exists()


def test_docker_native_console_has_real_terminal_without_fifo_or_process_rewrite(adapter, monkeypatch):
    """Wine creates Win32 console input handles only for terminal-backed Unix stdin."""
    module,server=adapter
    server.module=module
    server.data['module']='asrdserver'
    monkeypatch.setattr(module.proton,'wrap_command',lambda command,**kwargs:['wine',*command])
    process_command,_=module.get_start_command(server)
    requirements=module.get_runtime_requirements(server)
    spec=module.runtime_module.get_container_spec(server)
    assert requirements['stop_mode']=='docker-stop' and requirements['stdin_open'] is True
    assert spec['stop_mode']=='docker-stop' and spec['stdin_open'] is True and spec['tty'] is True
    native=module.proton.unwrap_runtime_command(process_command)
    assert spec['command']==native
    assert module.runtime_module.container_launch_command(spec)==native
    assert spec['env']['ALPHAGSM_WINEPREFIX']=='/srv/server/.wine'
