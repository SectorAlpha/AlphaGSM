"""CS2 setup deadlines preserve diagnostic evidence and never hide failures."""

import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture
def lifecycle(monkeypatch):
    helpers = importlib.import_module('tests.integration_tests.conftest')
    monkeypatch.setitem(sys.modules, 'conftest', helpers)
    path = Path(__file__).resolve().parents[1] / 'integration_tests/test_counterstrike2.py'
    spec = importlib.util.spec_from_file_location('cs2_setup_lifecycle', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_lifecycle_timeout_preserves_download_and_each_readiness_budget(lifecycle, request):
    helpers = importlib.import_module('tests.integration_tests.conftest')
    item = pytest.Function.from_parent(
        request.node.parent, name='cs2_timeout_contract',
        callobj=lifecycle.test_counterstrike2_lifecycle)
    item.add_marker(pytest.mark.integration)
    helpers.pytest_collection_modifyitems([item])

    expected = lifecycle.SETUP_TIMEOUT + 3 * lifecycle.START_TIMEOUT + lifecycle.STOP_TIMEOUT + 600
    # The global integration hook appends 1200s. The explicit function marker
    # must remain closest/first, which is the marker pytest-timeout consumes.
    assert item.get_closest_marker('timeout').args == (expected,)
    assert [mark.args[0] for mark in item.iter_markers('timeout')] == [expected, 1200]
    assert expected == 6090
    assert helpers.INTEGRATION_TEST_TIMEOUT == 1200


@pytest.mark.parametrize('payload', ['progress 42%', b'progress 42%', None])
def test_setup_timeout_fails_once_and_retains_both_streams(lifecycle, monkeypatch, tmp_path, payload):
    calls, logged, diagnostics = [], [], []

    def run(env, *args, timeout):
        calls.append((env, args, timeout))
        raise subprocess.TimeoutExpired(['alphagsm', *args], timeout, output=payload, stderr=payload)

    monkeypatch.setattr(lifecycle, 'run_alphagsm', run)
    monkeypatch.setattr(lifecycle, 'log_command_result', lambda label, result: logged.append((label, result)))
    monkeypatch.setattr(lifecycle, '_log_setup_download_diagnostics', lambda *args: diagnostics.append(args))
    env = {'HOME': str(tmp_path)}
    install = tmp_path / 'server'
    with pytest.raises(pytest.fail.Exception, match='setup exceeded 3600s'):
        lifecycle._run_setup(env, 'cs2', 27015, install)
    assert calls == [(env, ('cs2', 'setup', '-n', '27015', str(install)), 3600)]
    assert diagnostics == [(env, install)]
    assert len(logged) == 1 and logged[0][1].returncode == 124
    expected = 'progress 42%' if payload is not None else ''
    assert logged[0][1].stdout == expected
    assert logged[0][1].stderr == 'Timed out after 3600s\n' + expected


@pytest.mark.parametrize('status', [0, 3])
def test_setup_exit_result_cannot_become_a_skip(lifecycle, monkeypatch, tmp_path, status):
    result = subprocess.CompletedProcess(['alphagsm'], status, "App '730' state is 0x602", 'install failed')
    logged, diagnostics = [], []
    monkeypatch.setattr(lifecycle, 'run_alphagsm', lambda *_args, **_kwargs: result)
    monkeypatch.setattr(lifecycle, 'log_command_result', lambda _label, current: logged.append(current))
    monkeypatch.setattr(lifecycle, '_log_setup_download_diagnostics', lambda *args: diagnostics.append(args))
    if status:
        with pytest.raises(AssertionError, match='install failed'):
            lifecycle._run_setup({}, 'cs2', 27015, tmp_path)
        assert diagnostics == [({}, tmp_path)]
    else:
        assert lifecycle._run_setup({}, 'cs2', 27015, tmp_path) is result
        assert not diagnostics
    assert logged == [result]


def test_setup_diagnostics_bound_progress_and_exclude_account_state(lifecycle, monkeypatch, tmp_path):
    home, install = tmp_path / 'home', tmp_path / 'server'
    logs = home / 'Steam/logs'
    logs.mkdir(parents=True)
    (logs / 'content_log.txt').write_text('old-line\n' * 2000 + 'AppID 730 downloading 42%\n')
    (logs / 'connection_log.txt').write_text('credential-never-read')
    manifest = install / 'steamapps/appmanifest_730.acf'
    manifest.parent.mkdir(parents=True)
    manifest.write_text('"BytesToDownload" "73389778054"\n"BytesDownloaded" "42000"\n'
                        '"StateFlags" "1026"\n"LastOwner" "credential-never-read"\n'
                        '"UpdateResult" "not-a-number"\n')
    (home / 'Steam/loginusers.vdf').write_text('credential-never-read')
    results = []
    monkeypatch.setattr(lifecycle, 'log_command_result', lambda _label, result: results.append(result))
    monkeypatch.setattr(lifecycle.shutil, 'disk_usage', lambda _path: SimpleNamespace(total=100000, free=12345))
    lifecycle._log_setup_download_diagnostics({'HOME': str(home)}, install)
    assert len(results) == 1
    payload = json.loads(results[0].stdout)
    assert payload['disk'] == {'total_bytes': 100000, 'free_bytes': 12345}
    assert len(payload['steam_logs']) == 1
    assert len(payload['steam_logs'][0]['tail'].splitlines()) == 30
    assert payload['steam_logs'][0]['tail'].endswith('AppID 730 downloading 42%')
    assert payload['app_manifests'] == [{
        'path': str(manifest), 'counters': {
            'BytesToDownload': '73389778054', 'BytesDownloaded': '42000', 'StateFlags': '1026',
        },
    }]
    assert 'credential-never-read' not in results[0].stdout


def test_setup_diagnostics_survive_missing_install_and_steam_logs(lifecycle, monkeypatch, tmp_path):
    results = []
    monkeypatch.setattr(lifecycle, 'log_command_result', lambda _label, result: results.append(result))
    lifecycle._log_setup_download_diagnostics(
        {'HOME': str(tmp_path / 'missing-home')}, tmp_path / 'missing-parent/server')
    payload = json.loads(results[0].stdout)
    assert 'error' in payload['disk']
    assert payload['steam_logs'] == []
    assert payload['app_manifests'] == []
