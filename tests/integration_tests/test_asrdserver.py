"""AlphaGSM CLI lifecycle and native Workshop execution for Reactive Drop."""

import configparser
import json
import os
from pathlib import Path
import secrets
import sys
import time

import pytest

from tests.smoke_tests.asrd_workshop import change_map, query_native_maps
from conftest import (
    alphagsm_env, capture_alphagsm_stop, default_runtime_backend,
    effective_runtime_backend, pick_free_tcp_port_group, require_command_for_runtime,
    require_integration_opt_in, require_steamcmd_opt_in, run_alphagsm,
    run_and_assert_ok, wait_for_info_protocol, wait_for_udp_closed, write_config,
    resolve_wine_proton_runtime_image,
)

pytestmark = [pytest.mark.integration]
START_TIMEOUT = 600
STOP_TIMEOUT = 120


def test_asrdserver_lifecycle(tmp_path, workshop_source=None, workshop_identifier=None, runtime_backend=None):
    require_integration_opt_in()
    require_steamcmd_opt_in()
    module_name = 'asrdserver'
    runtime_backend = runtime_backend or os.environ.get('ALPHAGSM_TEST_RUNTIME_BACKEND', default_runtime_backend())
    require_command_for_runtime('screen', runtime_backend=runtime_backend, module_name=module_name)
    if effective_runtime_backend(runtime_backend, module_name=module_name) == 'process':
        require_command_for_runtime('wine', runtime_backend=runtime_backend, module_name=module_name)
    home = tmp_path / 'home'; home.mkdir()
    install_dir = tmp_path / 'server'
    config = tmp_path / 'alphagsm.conf'
    name = f'workshop-asrd-{runtime_backend}' if workshop_source else 'itasrdserver'
    write_config(config, home, session_tag='AlphaGSM-ASRD-IT#', runtime_backend=runtime_backend, module_name=module_name)
    steamcmd = os.environ.get('ALPHAGSM_ASRDSERVER_STEAMCMD_PATH', str(tmp_path / 'steamcmd'))
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config, encoding='utf-8')
    if not parser.has_section('downloader.steamcmd'):
        parser.add_section('downloader.steamcmd')
    parser.set('downloader.steamcmd', 'steamcmd_path', steamcmd)
    with config.open('w', encoding='utf-8') as handle:
        parser.write(handle)
    env = alphagsm_env(config)
    port = pick_free_tcp_port_group(3)
    run_and_assert_ok(env, name, 'create', module_name, allow_known_steamcmd_skip=False)
    run_and_assert_ok(env, name, 'set', 'clientport', str(port + 1))
    run_and_assert_ok(env, name, 'set', 'sourcetvport', str(port + 2))
    run_and_assert_ok(env, name, 'setup', '-n', str(port), str(install_dir), allow_known_steamcmd_skip=False)
    assert (install_dir / 'srcds_console.exe').is_file()
    assert Path(json.loads((home / 'conf' / f'{name}.json').read_text())['wineprefix']).is_relative_to(install_dir)
    if effective_runtime_backend(runtime_backend, module_name=module_name) == 'docker':
        run_and_assert_ok(env, name, 'set', 'image', resolve_wine_proton_runtime_image())
    password = secrets.token_hex(20)
    run_and_assert_ok(env, name, 'set', 'rconpassword', password)
    items = []
    if workshop_source:
        run_and_assert_ok(env, name, 'mod', 'add', workshop_source, workshop_identifier)
        run_and_assert_ok(env, name, 'mod', 'apply')
        data = json.loads((home / 'conf' / f'{name}.json').read_text())
        items = [entry['workshop_id'] for entry in data['mods']['desired']['workshop']]
        assert items
        workshop_config = install_dir / 'reactivedrop/cfg/workshop.cfg'
        with workshop_config.open('a') as handle:
            handle.write('// AlphaGSM test-owned operator comment\n')
    run_and_assert_ok(env, name, 'start', allow_known_steamcmd_skip=False)
    try:
        wait_for_info_protocol(env, name, 'a2s', START_TIMEOUT, expected_port=port)
        if items:
            _verify_workshop_execution(env, name, items, port, password)
        run_and_assert_ok(env, name, 'status')
        assert 'Server is responding' in run_and_assert_ok(env, name, 'query').stdout
        assert 'Protocol' in run_and_assert_ok(env, name, 'info').stdout
        data = json.loads(run_and_assert_ok(env, name, 'info', '--json').stdout.strip())
        assert data['protocol'] == 'a2s' and data['port'] == port
    finally:
        stopped = capture_alphagsm_stop(env, name, sys.exc_info()[1])
    assert stopped.returncode == 0, stopped.stderr or stopped.stdout
    wait_for_udp_closed('127.0.0.1', port, STOP_TIMEOUT)
    status = run_and_assert_ok(env, name, 'status').stdout.lower()
    assert 'not running' in status or "isn't running" in status or 'stopped' in status
    if items:
        run_and_assert_ok(env, name, 'mod', 'cleanup')
        assert workshop_config.read_text() == '// AlphaGSM test-owned operator comment\n'


def _verify_workshop_execution(env, name, items, port, password):
    item = os.environ.get('ALPHAGSM_ASRDSERVER_WORKSHOP_LOAD_ITEM', items[0])
    assert item in items
    map_name = os.environ.get('ALPHAGSM_ASRDSERVER_WORKSHOP_MAP')
    deadline, error, selected = time.monotonic() + 300, None, False
    while time.monotonic() < deadline:
        try:
            owners = query_native_maps('127.0.0.1', port, password)
            if not map_name:
                map_name = next((name for name, owner in owners.items() if owner == item), None)
            if map_name and owners.get(map_name) == item:
                if not selected:
                    change_map('127.0.0.1', port, password, map_name)
                    selected = True
                result = run_alphagsm(env, name, 'info', '--json')
                if result.returncode == 0:
                    data = json.loads(result.stdout.strip())
                    if data.get('protocol') == 'a2s' and data.get('map', '').lower() == map_name.lower():
                        # Re-query the running engine after level execution to exclude stale mappings.
                        assert query_native_maps('127.0.0.1', port, password).get(map_name) == item
                        print(f'ENGINE_WORKSHOP_MAP_LOADED {map_name} app=563560 item={item} native_mapping={owners}')
                        return
        except (ValueError, OSError, RuntimeError, AssertionError) as exc:
            error = exc
        time.sleep(2)
    output = run_and_assert_ok(env, name, 'logs', '-n', '20000').stdout
    pytest.fail(f'Reactive Drop failed native map mount/execution for {item}: {error}\n{output[-20000:]}')


@pytest.mark.skipif(os.environ.get('ALPHAGSM_RUN_ASRDSERVER_WORKSHOP') != '1',
                    reason='Opt in to external anonymous Reactive Drop Workshop lifecycle')
@pytest.mark.parametrize('runtime_backend', ['process', 'docker'])
def test_asrdserver_workshop_loads(tmp_path, runtime_backend):
    identifier = os.environ.get('ALPHAGSM_ASRDSERVER_WORKSHOP_COLLECTION')
    source = 'workshop-collection' if identifier else 'workshop'
    identifier = identifier or os.environ.get('ALPHAGSM_ASRDSERVER_WORKSHOP_ITEM', '848331447')
    test_asrdserver_lifecycle(tmp_path, source, identifier, runtime_backend)
