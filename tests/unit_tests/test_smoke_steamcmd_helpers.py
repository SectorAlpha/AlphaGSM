"""Tests for bash smoke SteamCMD helpers."""

from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
HELPERS_PATH = REPO_ROOT / "tests" / "smoke_tests" / "steamcmd_helpers.sh"


def _run_helper(command):
    return subprocess.run(
        [
            "bash",
            "-lc",
            f"source {HELPERS_PATH} >/dev/null 2>&1; {command}",
        ],
        cwd=str(REPO_ROOT),
        check=True,
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
