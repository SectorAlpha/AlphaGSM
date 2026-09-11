"""Keep transient artifact failures recoverable without losing required evidence."""

from pathlib import Path
import re


def test_test_artifact_upload_retries_once_and_preserves_final_failure():
    action = Path('.github/actions/upload-test-artifact/action.yml')
    assert action.exists()
    text = action.read_text()
    first, retry = text.split('    - name: Retry artifact upload')
    assert text.count('uses: actions/upload-artifact@v4') == 2
    assert 'continue-on-error: true' in first
    assert "always() && steps.first.outcome == 'failure'" in retry
    assert 'continue-on-error' not in retry
    assert 'overwrite: true' in retry
    for block in (first, retry):
        for field in ('name', 'path', 'if-no-files-found'):
            assert field + ': ${{ inputs.' + field + ' }}' in block


def test_smoke_results_survive_in_step_summary_before_artifact_upload():
    workflow = Path('.github/workflows/unittest.yaml').read_text()
    for job_name in ('smoke-test-standard', 'smoke-test-heavy'):
        # Job contents use four or more spaces, so split only an unindented job key.
        start = workflow.index('\n  ' + job_name + ':\n')
        next_job = workflow.find('\n  ', start + len('\n  ' + job_name + ':\n'))
        while next_job >= 0 and workflow[next_job + 3] == ' ':
            next_job = workflow.find('\n  ', next_job + 3)
        job = workflow[start:next_job if next_job >= 0 else None]
        summary = job.split('- name: Summarize smoke results', 1)[1].split('      - name:', 1)[0]
        assert 'if: always()' in summary
        assert 'GITHUB_STEP_SUMMARY' in summary
        assert 'smoke-results.txt' in summary
        assert job.index('Summarize smoke results') < job.index('Upload smoke test results')
        upload = job.split('- name: Upload smoke test results', 1)[1]
        assert 'uses: ./.github/actions/upload-test-artifact' in upload
        assert 'if-no-files-found: error' in upload


def test_expensive_rechecks_stop_when_the_workflow_is_cancelled():
    """Superseded matrices must release the workflow concurrency slot."""
    workflow = Path('.github/workflows/unittest.yaml').read_text()
    jobs = dict(re.findall(r'^  ([\w-]+):\n(.*?)(?=^  [\w-]+:|\Z)',
                           workflow, re.MULTILINE | re.DOTALL))
    for name in ('collect-integration-rechecks', 'integration-flake-recheck'):
        condition = re.search(r'^    if: (.+)$', jobs[name], re.MULTILINE).group(1)
        assert '!cancelled()' in condition
        assert 'always()' not in condition
    assert "needs.collect-integration-rechecks.outputs.has_rechecks == 'true'" in jobs['integration-flake-recheck']
    # The required final report and diagnostic uploads still run after failure.
    assert '    if: always()' in jobs['summarize-tests']
    assert '        if: always()' in jobs['integration-flake-recheck']


def test_cancelled_backend_job_does_not_start_docker_integration_suite():
    """A superseded process lane must not launch the expensive Docker lane."""

    workflow = Path('.github/workflows/unittest.yaml').read_text()
    backend_job = workflow.split('  backend-integration-test:', 1)[1].split(
        '\n  windows-minecraft-integration:', 1
    )[0]
    docker_step = backend_job.split(
        '- name: Backend Docker Integration Tests (active matrix cases)', 1
    )[1].split('\n      - name:', 1)[0]

    condition = re.search(r'^        if: (.+)$', docker_step, re.MULTILINE).group(1)
    assert 'always()' in condition
    assert '!cancelled()' in condition
