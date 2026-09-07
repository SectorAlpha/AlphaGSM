"""Tests for bash smoke SteamCMD helpers."""

from pathlib import Path
import subprocess
import shlex

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPERS_PATH = REPO_ROOT / "tests" / "smoke_tests" / "steamcmd_helpers.sh"


def _run_helper(command, *, check=True):
    return subprocess.run(
        [
            "bash",
            "-lc",
            f"source {HELPERS_PATH} >/dev/null 2>&1; {command}",
        ],
        cwd=str(REPO_ROOT),
        check=check,
        text=True,
        capture_output=True,
    )


def test_parse_recommended_port_overrides_line_strips_trailing_commas():
    result = _run_helper(
        "parse_recommended_port_overrides_line "
        "'Recommended free port set: blobsyncport=9701, port=48174, queryport=27017'"
    )

    assert result.stdout.splitlines() == [
        "blobsyncport=9701",
        "port=48174",
        "queryport=27017",
    ]


@pytest.mark.parametrize("command", [
    "wait_for_ready /nonexistent/alphagsm-test.log 0",
    "wait_for_glob_ready '/nonexistent/alphagsm-test-*.log' 0",
    "wait_for_info_protocol testserver quake2 0",
    "run_stop_or_skip testserver",
])
def test_readiness_timeout_and_failed_stop_are_failures(command):
    result = _run_helper(
        'run_alphagsm() { echo "fixture command: $*"; return 1; }; '
        + command,
        check=False,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "skipping" not in result.stderr


def test_info_timeout_captures_runtime_before_cleanup(tmp_path):
    evidence = tmp_path / "calls.log"
    result = _run_helper(
        'run_alphagsm() { echo "$*" >> ' + shlex.quote(str(evidence)) + '; }; '
        'wait_for_info_protocol testserver quake2 0',
        check=False,
    )
    assert result.returncode != 0
    assert evidence.read_text().splitlines() == ["testserver doctor", "testserver logs -n 200"]
