"""Tests for the CI status polling helper."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.helpers import load_module_from_repo


SCRIPT_PATH = Path("scripts/ci_status.py")


def load_ci_status_module():
    assert SCRIPT_PATH.exists(), f"missing CI helper: {SCRIPT_PATH}"
    return load_module_from_repo("ci_status_helper", str(SCRIPT_PATH))


def _completed_run_payload():
    return {
        "status": "completed",
        "conclusion": "failure",
        "workflowName": "unit-test",
        "headBranch": "release_v1",
        "headSha": "deadbeefcafebabe",
        "url": "https://github.com/cosmosquark/AlphaGSM/actions/runs/123",
        "jobs": [
            {"name": "lint", "status": "completed", "conclusion": "success"},
            {"name": "integration", "status": "completed", "conclusion": "failure"},
            {"name": "docs", "status": "completed", "conclusion": "cancelled"},
        ],
    }


def test_main_reports_failed_jobs_and_key_log_lines(monkeypatch, capsys):
    ci_status = load_ci_status_module()
    calls = []

    def fake_run(command, check=False, capture_output=False, text=False):
        calls.append(command)
        if "--log-failed" in command:
            return SimpleNamespace(
                returncode=0,
                stdout="\n".join(
                    [
                        "integration/build  Build",
                        "integration/build  Error: missing artifact",
                        "integration/build  returned non-zero exit status 1",
                        "docs/check  skipped",
                    ]
                ),
                stderr="",
            )
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(_completed_run_payload()),
            stderr="",
        )

    monkeypatch.setattr(ci_status.subprocess, "run", fake_run)

    exit_code = ci_status.main(["123", "--once"])

    out = capsys.readouterr().out
    assert exit_code == 1
    assert "status=completed conclusion=failure" in out
    assert "failed jobs:" in out
    assert "- integration" in out
    assert "Error: missing artifact" in out
    assert "returned non-zero exit status 1" in out
    assert any("--log-failed" in command for command in calls)


def test_main_once_reports_in_progress_run_without_following(monkeypatch, capsys):
    ci_status = load_ci_status_module()
    calls = []

    in_progress_payload = {
        "status": "in_progress",
        "conclusion": None,
        "workflowName": "unit-test",
        "headBranch": "feature/ci",
        "headSha": "feedface12345678",
        "url": "https://github.com/cosmosquark/AlphaGSM/actions/runs/456",
        "jobs": [],
    }

    def fake_run(command, check=False, capture_output=False, text=False):
        calls.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(in_progress_payload),
            stderr="",
        )

    monkeypatch.setattr(ci_status.subprocess, "run", fake_run)

    exit_code = ci_status.main(["456", "--once"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "status=in_progress conclusion=None" in out
    assert len(calls) == 1


def test_helper_functions_filter_failed_jobs_and_logs():
    ci_status = load_ci_status_module()

    run = {
        "jobs": [
            {"name": "lint", "status": "completed", "conclusion": "success"},
            {"name": "integration", "status": "completed", "conclusion": "failure"},
            {"name": "docs", "status": "completed", "conclusion": "cancelled"},
            {"name": "build", "status": "completed", "conclusion": None},
        ]
    }
    assert ci_status.failed_jobs(run) == ["integration"]

    log_text = "\n".join(
        [
            "start",
            "everything fine",
            "Build Error: missing artifact",
            "stack trace line 1",
            "stack trace line 2",
            "tail context",
            "final tail line",
        ]
    )
    key_lines = ci_status.extract_key_log_lines(log_text, limit=4)
    assert "Build Error: missing artifact" in key_lines
    assert "final tail line" in key_lines


def test_main_reports_gh_failures_without_traceback(monkeypatch, capsys):
    ci_status = load_ci_status_module()

    def fake_run(command, check=False, capture_output=False, text=False):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="gh not authenticated",
        )

    monkeypatch.setattr(ci_status.subprocess, "run", fake_run)

    exit_code = ci_status.main(["123", "--once"])

    err = capsys.readouterr().err
    assert exit_code == 2
    assert "gh command failed" in err
    assert "gh not authenticated" in err
