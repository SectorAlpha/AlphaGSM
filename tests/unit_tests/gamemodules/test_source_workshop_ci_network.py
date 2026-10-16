"""ASRD/NS2 Workshop probes must address their actual CI runtime namespace."""

import configparser
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[3]


def integration_module(name, monkeypatch):
    from tests.integration_tests import conftest as helpers
    monkeypatch.setitem(sys.modules, 'conftest', helpers)
    path = ROOT / 'tests/integration_tests' / f'test_{name}.py'
    spec = importlib.util.spec_from_file_location(f'_{name}_workshop_network', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('name,entrypoint,home_name', [
    ('bb2server', 'test_bb2server_lifecycle', 'home'),
    ('doiserver', 'test_doiserver_lifecycle', 'home'),
    ('insserver', 'test_insserver_lifecycle', 'home'),
    ('nmrihserver', 'test_nmrihserver_lifecycle', 'home'),
    ('tf2', 'test_tf2_download_install_and_start', 'alphagsm-home'),
])
@pytest.mark.parametrize('backend', ['process', 'docker'])
@pytest.mark.parametrize('shared_work_dir', [False, True])
def test_source_workshop_lifecycles_reach_create_with_one_steamcmd_section(
        tmp_path, monkeypatch, name, entrypoint, home_name, backend, shared_work_dir):
    module = integration_module(name, monkeypatch)
    if shared_work_dir:
        monkeypatch.setenv('ALPHAGSM_WORK_DIR', str(tmp_path / 'shared'))
    else:
        monkeypatch.delenv('ALPHAGSM_WORK_DIR', raising=False)
    override = str(tmp_path / 'SteamCMD 100% override')
    monkeypatch.setenv(f'ALPHAGSM_{name.upper()}_STEAMCMD_PATH', override)
    for helper in ('require_integration_opt_in', 'require_steamcmd_opt_in', 'require_command_for_runtime'):
        monkeypatch.setattr(module, helper, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, 'pick_free_tcp_port_group', lambda _count: 17000)
    if hasattr(module, 'detect_query_host'):
        monkeypatch.setattr(module, 'detect_query_host', lambda: '127.0.0.1')

    class BeforeCreate(Exception):
        pass

    def inspect(env, _server, action, *_args, **_kwargs):
        assert action == 'create'
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(env['ALPHAGSM_CONFIG_LOCATION'], encoding='utf-8')
        assert parser.sections().count('downloader.steamcmd') == 1
        assert parser['downloader.steamcmd']['steamcmd_path'] == override
        assert parser['runtime']['backend'] == backend
        assert parser['server']['datapath'] == str(tmp_path / home_name / 'conf')
        raise BeforeCreate

    monkeypatch.setattr(module, 'run_and_assert_ok', inspect)
    with pytest.raises(BeforeCreate):
        getattr(module, entrypoint)(tmp_path, 'workshop', '123', backend)


@pytest.mark.parametrize('name', ['asrdserver'])
@pytest.mark.parametrize('backend,hosts,expected', [
    ('process', ('127.0.0.1', '172.17.0.1'), '127.0.0.1'),
    ('docker', ('127.0.0.1', '172.17.0.1'), '172.17.0.1'),
    ('docker', ('127.0.0.1',), '127.0.0.1'),
])
def test_native_admin_host_distinguishes_manager_process_and_sibling_docker(
        monkeypatch, name, backend, hosts, expected):
    module = integration_module(name, monkeypatch)
    monkeypatch.setattr(module, 'effective_runtime_backend', lambda value, **_kwargs: value)
    monkeypatch.setattr(module, '_runtime_probe_hosts', lambda host: hosts if host == '127.0.0.1' else ())
    assert module._workshop_admin_host(backend) == expected


def test_asrd_native_mapping_change_and_post_load_probe_use_resolved_host(monkeypatch):
    module = integration_module('asrdserver', monkeypatch)
    monkeypatch.setenv('ALPHAGSM_ASRDSERVER_WORKSHOP_LOAD_ITEM', '123')
    monkeypatch.setenv('ALPHAGSM_ASRDSERVER_WORKSHOP_MAP', 'fixture_map')
    observations = []
    def maps(host, port, password):
        observations.append(('maps', host, port, password))
        return {'fixture_map': '123'}
    monkeypatch.setattr(module, 'query_native_maps', maps)
    monkeypatch.setattr(module, 'change_map', lambda *args: observations.append(('change', *args)))
    monkeypatch.setattr(module, 'run_alphagsm', lambda *_args: SimpleNamespace(
        returncode=0, stdout=json.dumps({'protocol': 'a2s', 'map': 'fixture_map'})))
    module._verify_workshop_execution({}, 'asrd', ['123'], 27015, 'private', host='172.17.0.1')
    assert observations == [('maps', '172.17.0.1', 27015, 'private'),
                            ('change', '172.17.0.1', 27015, 'private', 'fixture_map'),
                            ('maps', '172.17.0.1', 27015, 'private')]


@pytest.mark.parametrize('container_name', [None, 'owned-ns2-container'])
def test_ns2_native_origin_change_and_post_load_probe_use_resolved_transport(monkeypatch, container_name):
    module = integration_module('ns2server', monkeypatch)
    monkeypatch.setenv('ALPHAGSM_NS2SERVER_WORKSHOP_LOAD_ITEM', '123')
    monkeypatch.setenv('ALPHAGSM_NS2SERVER_WORKSHOP_MAP', 'ns2_fixture')
    observations = []
    def origins(host, port, user, password, **transport):
        observations.append(('origins', host, port, user, password, transport))
        return [{'name': 'ns2_fixture', 'modId': 123}]
    monkeypatch.setattr(module, 'read_map_origins', origins)
    monkeypatch.setattr(module, 'change_map', lambda *args, **transport: observations.append(('change', *args, transport)))
    monkeypatch.setattr(module, 'run_alphagsm', lambda *_args: SimpleNamespace(
        returncode=0, stdout=json.dumps({'protocol': 'a2s', 'port': 27016, 'map': 'ns2_fixture'})))
    module._verify_workshop_execution({}, 'ns2', ['123'], 27016, 27017, host='127.0.0.1',
                                      container_name=container_name)
    transport = {'container_name': container_name} if container_name else {}
    assert observations == [('origins', '127.0.0.1', 27017, 'admin', 'CHANGE_ME', transport),
                            ('change', '127.0.0.1', 27017, 'admin', 'CHANGE_ME', 'ns2_fixture', transport),
                            ('origins', '127.0.0.1', 27017, 'admin', 'CHANGE_ME', transport)]


@pytest.mark.parametrize('shared_work_dir', [False, True])
@pytest.mark.parametrize('custom_steamcmd', [False, True])
def test_ns2_workshop_steamcmd_override_preserves_one_valid_section(
        tmp_path, monkeypatch, shared_work_dir, custom_steamcmd):
    module = integration_module('ns2server', monkeypatch)
    if shared_work_dir:
        monkeypatch.setenv('ALPHAGSM_WORK_DIR', str(tmp_path / 'shared'))
    else:
        monkeypatch.delenv('ALPHAGSM_WORK_DIR', raising=False)
    override = str(tmp_path / 'custom 100% steamcmd')
    if custom_steamcmd:
        monkeypatch.setenv('ALPHAGSM_NS2SERVER_STEAMCMD_PATH', override)
    else:
        monkeypatch.delenv('ALPHAGSM_NS2SERVER_STEAMCMD_PATH', raising=False)
    for name in ('require_integration_opt_in', 'require_steamcmd_opt_in', 'require_command_for_runtime'):
        monkeypatch.setattr(module, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, 'pick_free_tcp_port_group', lambda _count: 27015)

    class BeforeCreate(Exception):
        pass

    def inspect(env, _name, action, *_args, **_kwargs):
        assert action == 'create'
        parser = configparser.ConfigParser(interpolation=None)
        parser.read(env['ALPHAGSM_CONFIG_LOCATION'], encoding='utf-8')
        assert parser.sections().count('downloader.steamcmd') == 1
        expected = override if custom_steamcmd else str(tmp_path / 'steamcmd')
        assert parser['downloader.steamcmd']['steamcmd_path'] == expected
        assert parser['runtime']['backend'] == 'docker'
        assert parser['server']['datapath'] == str(tmp_path / 'home/conf')
        raise BeforeCreate
    monkeypatch.setattr(module, 'run_and_assert_ok', inspect)
    with pytest.raises(BeforeCreate):
        module._run_ns2_workshop_lifecycle(tmp_path, 'workshop', '123', 'docker')


def test_ns2_workshop_failed_start_attempts_stop_without_masking_error(tmp_path, monkeypatch):
    module = integration_module('ns2server', monkeypatch)
    for name in ('require_integration_opt_in', 'require_steamcmd_opt_in', 'require_command_for_runtime'):
        monkeypatch.setattr(module, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, 'pick_free_tcp_port_group', lambda _count: 27015)
    failure = RuntimeError('native startup failed')
    stopped = []
    def command(_env, server_name, action, *_args, **_kwargs):
        if action == 'setup':
            install = tmp_path / 'server'
            (install / server_name / 'Workshop').mkdir(parents=True)
            (install / 'logs').mkdir()
            (install / 'x64').mkdir()
            (install / 'x64/server_linux').touch()
        if action == 'start':
            raise failure
        return SimpleNamespace(returncode=0, stdout='', stderr='')
    monkeypatch.setattr(module, 'run_and_assert_ok', command)
    monkeypatch.setattr(module, 'capture_alphagsm_stop', lambda *args: stopped.append(args[2]))
    with pytest.raises(RuntimeError) as caught:
        module._run_ns2_workshop_lifecycle(tmp_path, None, None, 'process')
    assert caught.value is failure and stopped == [failure]
