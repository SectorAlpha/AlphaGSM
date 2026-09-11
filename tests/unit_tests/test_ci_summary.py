"""Exercise the required CI gate with real artifact files and needs outcomes."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tests.helpers import REPO_ROOT


REQUIRED = (
    'build lint unit-test coverage binary-build-smoke classify-changes '
    'discover-smoke-tests discover-integration-tests build-integration-image '
    'build-java-runtime build-quake-linux-runtime build-simple-tcp-runtime '
    'build-steamcmd-linux-runtime build-wine-proton-runtime backend-smoke-test '
    'backend-integration-test '
    'windows-minecraft-integration macos-minecraft-integration collect-integration-rechecks'
).split()
LANES = ('smoke_standard', 'smoke_heavy', 'integration_standard', 'integration_heavy')
CASE = '<testcase classname="tests.integration_tests.test_alpha" name="test_lifecycle">{}</testcase>'


def context():
    needs = {name: {'result': 'success', 'outputs': {}} for name in REQUIRED}
    outputs = {'game_test_mode': 'skip'}
    for lane in LANES:
        outputs[lane + '_matrix'] = json.dumps({'include': []})
        outputs['has_' + lane + '_tests'] = 'false'
        needs[lane.replace('_', '-test-')] = {'result': 'skipped'}
    needs['classify-changes']['outputs'] = outputs
    needs['collect-integration-rechecks']['outputs'] = {
        'matrix': '{"include":[]}', 'has_rechecks': 'false'}
    needs['integration-flake-recheck'] = {'result': 'skipped'}
    return needs


def report(root, artifact, filename='results.xml', content=None):
    path = root / artifact / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content is not None else '<testsuite>' + CASE.format('') + '</testsuite>')


def backend(root):
    for filename in ('backend-process-results.xml', 'backend-docker-results.xml'):
        report(root, 'backend-integration-results-linux', filename)


def select_integration(needs):
    outputs = needs['classify-changes']['outputs']
    outputs.update(game_test_mode='targeted', has_integration_standard_tests='true')
    outputs['integration_standard_matrix'] = json.dumps({'include': [
        {'label': 'alpha-process', 'files': 'tests/integration_tests/test_alpha.py', 'runtime_backend': 'process'}]})
    needs['integration-test-standard']['result'] = 'success'
    return 'integration-results-standard-alpha-process'


def gate(root, needs):
    env = dict(os.environ, CI_NEEDS_JSON=json.dumps(needs))
    return subprocess.run([sys.executable, str(REPO_ROOT / 'scripts/summarize_tests.py'), str(root)],
                          text=True, capture_output=True, env=env, check=False)


def test_gate_allows_explicit_docs_routing_with_required_jobs_and_backend_reports(tmp_path):
    backend(tmp_path)
    assert gate(tmp_path, context()).returncode == 0


@pytest.mark.parametrize('damage', ['missing-artifacts', 'malformed', 'empty', 'missing-job',
                                    'cancelled-job', 'skipped-job', 'failed-binary', 'missing-backend-report'])
def test_gate_fails_closed(tmp_path, damage):
    needs = context()
    backend(tmp_path)
    if damage == 'missing-artifacts':
        for path in tmp_path.rglob('*.xml'):
            path.unlink()
    elif damage in ('malformed', 'empty'):
        report(tmp_path, 'backend-integration-results-linux', 'backend-process-results.xml',
               'not xml' if damage == 'malformed' else '<testsuite/>')
    elif damage == 'missing-job':
        del needs['lint']
    elif damage == 'cancelled-job':
        needs['unit-test']['result'] = 'cancelled'
    elif damage == 'skipped-job':
        needs['backend-smoke-test']['result'] = 'skipped'
    elif damage == 'failed-binary':
        needs['binary-build-smoke']['result'] = 'failure'
    else:
        (tmp_path / 'backend-integration-results-linux/backend-docker-results.xml').unlink()
    result = gate(tmp_path, needs)
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize('damage', ['missing-report', 'missing-exit-code', 'collection-error', 'missing-test-file'])
def test_selected_integration_requires_complete_reports(tmp_path, damage):
    needs = context()
    backend(tmp_path)
    artifact = select_integration(needs)
    if damage != 'missing-report':
        report(tmp_path, artifact)
        if damage != 'missing-exit-code':
            report(tmp_path, artifact, 'exit-code.txt', '2' if damage == 'collection-error' else '0')
        if damage == 'missing-test-file':
            outputs = needs['classify-changes']['outputs']
            matrix = json.loads(outputs['integration_standard_matrix'])
            matrix['include'][0]['files'] += ' tests/integration_tests/test_beta.py'
            outputs['integration_standard_matrix'] = json.dumps(matrix)
    assert gate(tmp_path, needs).returncode == 1


@pytest.mark.parametrize('recheck', ['pass', 'fail', 'skip', 'missing', 'wrong-lane', 'duplicate'])
def test_one_matching_recheck_can_recover_initial_failure(tmp_path, recheck):
    needs = context()
    backend(tmp_path)
    artifact = select_integration(needs)
    report(tmp_path, artifact, content='<testsuite>' + CASE.format('<failure message="timeout"/>') + '</testsuite>')
    report(tmp_path, artifact, 'exit-code.txt', '1')
    entry = {'source_artifact': artifact, 'nodeid': 'tests/integration_tests/test_alpha.py::test_lifecycle',
             'runtime_backend': 'process', 'runner_class': 'standard'}
    needs['collect-integration-rechecks']['outputs'] = {'has_rechecks': 'true', 'matrix': json.dumps({'include': [entry]})}
    needs['integration-flake-recheck']['result'] = 'success' if recheck != 'fail' else 'failure'
    if recheck != 'missing':
        source = artifact.replace('process', 'docker') if recheck == 'wrong-lane' else artifact
        payload = {'fail': '<failure/>', 'skip': '<skipped/>'}.get(recheck, '')
        report(tmp_path, 'integration-recheck-results-' + source + '-0', 'recheck-results.xml',
               '<testsuite>' + CASE.format(payload) + '</testsuite>')
        if recheck == 'duplicate':
            report(tmp_path, 'integration-recheck-results-' + source + '-1', 'recheck-results.xml')
    result = gate(tmp_path, needs)
    assert result.returncode == (0 if recheck == 'pass' else 1), result.stdout + result.stderr
    if recheck == 'pass':
        assert 'initial failure retained' in result.stdout


@pytest.mark.parametrize('damage', ['empty', 'partial', 'duplicate', 'malformed', 'failed'])
def test_selected_smoke_artifact_must_account_for_every_script(tmp_path, damage):
    needs = context()
    backend(tmp_path)
    outputs = needs['classify-changes']['outputs']
    outputs.update(game_test_mode='targeted', has_smoke_standard_tests='true')
    outputs['smoke_standard_matrix'] = json.dumps({'include': [
        {'label': 'batch', 'scripts': 'tests/smoke_tests/run_a.sh tests/smoke_tests/run_b.sh'}]})
    needs['smoke-test-standard']['result'] = 'success'
    passed = 'PASSED: tests/smoke_tests/run_a.sh\n'
    contents = {'empty': '', 'partial': passed, 'duplicate': passed + passed,
                'malformed': 'garbage\n', 'failed': passed + 'FAILED: tests/smoke_tests/run_b.sh\n'}
    report(tmp_path, 'smoke-results-standard-batch', 'smoke-results.txt', contents[damage])
    assert gate(tmp_path, needs).returncode == 1


def test_summary_rejects_inconsistent_junit_counts(tmp_path):
    backend(tmp_path)
    report(tmp_path, 'backend-integration-results-linux', 'backend-process-results.xml',
           '<testsuite tests="1" failures="1">' + CASE.format('') + '</testsuite>')
    assert gate(tmp_path, context()).returncode == 1
