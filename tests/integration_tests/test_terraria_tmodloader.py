"""tModLoader CLI lifecycle and execution of a public multiplayer Workshop mod."""

import json
import os
import sys
from uuid import uuid4

import pytest
from tests.smoke_tests.tmodloader_workshop import assert_census_loaded

from conftest import (
    alphagsm_env, assert_alphagsm_result_ok, capture_alphagsm_stop,
    default_runtime_backend,
    pick_free_tcp_port, require_command_for_runtime, require_integration_opt_in,
    require_steamcmd_opt_in, resolve_steamcmd_linux_runtime_image,
    run_and_assert_ok, wait_for_runtime_log_marker, wait_for_tcp_closed, write_config,
)

pytestmark = pytest.mark.integration
MODULE = 'terraria.tmodloader'
START_TIMEOUT = 900
CENSUS_ITEM = '2687866031'
BACKENDS = ([os.environ.get('ALPHAGSM_TEST_RUNTIME_BACKEND', default_runtime_backend())]
            if os.environ.get('ALPHAGSM_TEST_RUNTIME_BACKEND') else ['process', 'docker'])


def _assert_census_execution(env, name):
    """Require fresh command output, rather than a package/configuration listing."""
    assert_census_loaded(lambda *args: run_and_assert_ok(env, name, *args).stdout)


def _lifecycle(tmp_path, backend, workshop):
    require_integration_opt_in()
    if workshop:
        require_steamcmd_opt_in()
    require_command_for_runtime('screen', runtime_backend=backend, module_name=MODULE)
    home = tmp_path / 'home'
    home.mkdir()
    install = tmp_path / 'server'
    config = tmp_path / 'alphagsm.conf'
    name = 'ittml' + uuid4().hex[:8]
    write_config(config, home, session_tag='AlphaGSM-TML-IT#',
                 runtime_backend=backend, module_name=MODULE)
    env = alphagsm_env(config)
    port = pick_free_tcp_port()
    run_and_assert_ok(env, name, 'create', MODULE)
    if backend == 'docker':
        run_and_assert_ok(env, name, 'set', 'image', resolve_steamcmd_linux_runtime_image())
    run_and_assert_ok(env, name, 'setup', '-n', str(port), str(install),
                      timeout=START_TIMEOUT, allow_known_steamcmd_skip=False)
    if workshop:
        assert not (install / 'Mods/Census.tmod').exists()
        run_and_assert_ok(env, name, 'mod', 'add', 'workshop',
                          'https://steamcommunity.com/sharedfiles/filedetails/?id=' + CENSUS_ITEM)
        run_and_assert_ok(env, name, 'mod', 'apply', timeout=START_TIMEOUT,
                          allow_known_steamcmd_skip=False)
    try:
        run_and_assert_ok(env, name, 'start', '--autocreate')
        wait_for_runtime_log_marker(env, name, ['Listening on port', "Type 'help'"], START_TIMEOUT)
        run_and_assert_ok(env, name, 'status')
        query = run_and_assert_ok(env, name, 'query')
        assert 'Terraria handshake' in query.stdout
        info = run_and_assert_ok(env, name, 'info')
        assert 'Terraria handshake' in info.stdout
        payload = json.loads(run_and_assert_ok(env, name, 'info', '--json').stdout)
        assert payload['protocol'] == 'terraria'
        if workshop:
            _assert_census_execution(env, name)
    finally:
        stopped = capture_alphagsm_stop(env, name, sys.exc_info()[1], timeout=90)
    assert_alphagsm_result_ok(stopped)
    wait_for_tcp_closed('127.0.0.1', port, 90)
    if workshop:
        run_and_assert_ok(env, name, 'mod', 'cleanup')
        assert not (install / 'Mods/Census.tmod').exists()
        assert 'Census' not in json.loads((install / 'Mods/enabled.json').read_text())


@pytest.mark.parametrize('backend', BACKENDS)
def test_tmodloader_lifecycle(tmp_path, backend):
    """Public releases self-provision both runtimes without provider credentials."""
    _lifecycle(tmp_path, backend, False)


@pytest.mark.skipif(os.environ.get('ALPHAGSM_RUN_WORKSHOP') != '1',
                    reason='Set ALPHAGSM_RUN_WORKSHOP=1 for anonymous mod execution checks')
@pytest.mark.parametrize('backend', BACKENDS)
def test_tmodloader_workshop_lifecycle(tmp_path, backend):
    """Census must execute its own console command inside the fresh game engine."""
    _lifecycle(tmp_path, backend, True)
