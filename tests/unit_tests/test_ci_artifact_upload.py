"""Keep transient artifact failures recoverable without losing required evidence."""

from pathlib import Path


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
