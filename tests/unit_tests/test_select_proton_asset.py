"""Unit tests for selecting a Proton-GE release asset by host architecture."""

import json
import os
import subprocess
import sys
from pathlib import Path


SELECTOR = Path("scripts/select_proton_asset.py")
INSTALLER = Path("scripts/install_proton.sh")


def _write_executable(path, contents):
    path.write_text(contents, encoding="utf-8")
    path.chmod(0o755)


def test_selects_x86_64_asset_when_arm_archive_is_listed_first():
    release = {
        "assets": [
            {
                "name": "GE-Proton11-1-aarch64.tar.gz",
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
            },
            {
                "name": "GE-Proton11-1.tar.gz",
                "browser_download_url": "https://example.invalid/GE-Proton11-1.tar.gz",
            },
        ]
    }

    result = subprocess.run(
        [sys.executable, str(SELECTOR), "x86_64"],
        input=json.dumps(release),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "https://example.invalid/GE-Proton11-1.tar.gz"


def test_selects_aarch64_asset_for_arm_runner():
    release = {
        "assets": [
            {
                "name": "GE-Proton11-1-aarch64.tar.gz",
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
            },
            {
                "name": "GE-Proton11-1.tar.gz",
                "browser_download_url": "https://example.invalid/GE-Proton11-1.tar.gz",
            },
        ]
    }

    result = subprocess.run(
        [sys.executable, str(SELECTOR), "aarch64"],
        input=json.dumps(release),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (
        result.stdout.strip()
        == "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
    )


def test_accepts_gh_release_view_asset_url_field():
    release = {
        "assets": [
            {
                "name": "GE-Proton11-1-aarch64.tar.gz",
                "browserDownloadUrl": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
            },
            {
                "name": "GE-Proton11-1.tar.gz",
                "browserDownloadUrl": "https://example.invalid/GE-Proton11-1.tar.gz",
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1.tar.gz"
                ),
            },
        ]
    }

    result = subprocess.run(
        [sys.executable, str(SELECTOR), "x86_64"],
        input=json.dumps(release),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "https://example.invalid/GE-Proton11-1.tar.gz"


def test_installer_downloads_asset_matching_host_architecture(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    curl_log = tmp_path / "curl.log"
    install_dir = tmp_path / "proton"
    release = {
        "assets": [
            {
                "name": "GE-Proton11-1-aarch64.tar.gz",
                "browserDownloadUrl": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1-aarch64.tar.gz"
                ),
            },
            {
                "name": "GE-Proton11-1.tar.gz",
                "browserDownloadUrl": "https://example.invalid/GE-Proton11-1.tar.gz",
                "browser_download_url": (
                    "https://example.invalid/GE-Proton11-1.tar.gz"
                ),
            },
        ]
    }

    _write_executable(fake_bin / "uname", "#!/bin/sh\nprintf 'x86_64\\n'\n")
    _write_executable(
        fake_bin / "gh",
        "#!/bin/sh\nprintf '%s\\n' \"$PROTON_RELEASE_JSON\"\n",
    )
    _write_executable(fake_bin / "sleep", "#!/bin/sh\nexit 0\n")
    _write_executable(
        fake_bin / "curl",
        """#!/bin/sh
case "$*" in
    *api.github.com*) printf '%s\n' "$PROTON_RELEASE_JSON" ;;
    *) printf '%s\n' "$*" >> "$CURL_LOG" ;;
esac
""",
    )
    _write_executable(
        fake_bin / "tar",
        """#!/bin/sh
while [ "$#" -gt 0 ]; do
    if [ "$1" = "-C" ]; then
        shift
        install_dir="$1"
        break
    fi
    shift
done
mkdir -p "$install_dir/GE-Proton11-1"
touch "$install_dir/GE-Proton11-1/proton"
""",
    )

    env = {
        **os.environ,
        "CURL_LOG": str(curl_log),
        "HOME": str(tmp_path),
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "PROTON_GE_DIR": str(install_dir),
        "PROTON_RELEASE_JSON": json.dumps(release),
    }
    result = subprocess.run(
        ["bash", str(INSTALLER), "proton"],
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert curl_log.read_text(encoding="utf-8").strip() == (
        "-L https://example.invalid/GE-Proton11-1.tar.gz"
    )
