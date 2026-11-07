"""CI diagnostic capture preserves the original failure and emits JSON artifacts."""
import importlib
import json
import subprocess

import pytest


@pytest.mark.parametrize('stage', ['create', 'setup', 'start', 'query', 'stop'])
def test_command_failure_emits_diagnostic_artifact_without_masking_exit(tmp_path, monkeypatch, stage):
    helpers = importlib.import_module('tests.integration_tests.conftest')
    initial = subprocess.CompletedProcess([], 7, 'failed', '')
    commands = []
    def run(command, **kwargs):
        commands.append(command)
        if 'doctor' in command:
            return subprocess.CompletedProcess(command, 1, '{"schema_version":1,"status":"failed","checks":[]}', '')
        return initial
    monkeypatch.setattr(helpers.subprocess, 'run', run)
    env = {'ALPHAGSM_DIAGNOSTICS_DIR': str(tmp_path)}
    result = helpers.run_alphagsm(env, 'alpha', stage)
    assert result is initial
    paths = list(tmp_path.glob('*.json'))
    assert len(paths) == 1
    payload = json.loads(paths[0].read_text())
    assert payload['stage'] == stage
    assert payload['status'] == 'failed'
    assert commands[-1][-3:] == ['alpha', 'doctor', '--json']


def test_diagnostic_collection_failure_does_not_replace_command_failure(tmp_path, monkeypatch):
    helpers = importlib.import_module('tests.integration_tests.conftest')
    initial = subprocess.CompletedProcess([], 7, '', '')
    def run(command, **kwargs):
        if 'doctor' in command:
            raise subprocess.TimeoutExpired(command, 30)
        return initial
    monkeypatch.setattr(helpers.subprocess, 'run', run)
    result = helpers.run_alphagsm({'ALPHAGSM_DIAGNOSTICS_DIR': str(tmp_path)}, 'alpha', 'setup')
    assert result is initial
    payload = json.loads(next(tmp_path.glob('*.json')).read_text())
    assert payload['status'] == 'unavailable'
