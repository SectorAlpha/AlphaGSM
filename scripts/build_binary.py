#!/usr/bin/env python3
"""Build a standalone AlphaGSM binary with PyInstaller."""

from pathlib import Path
import os
import shutil
import sys

from PyInstaller.__main__ import run as pyinstaller_run


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist-binary"
BUILD_DIR = REPO_ROOT / "build" / "pyinstaller"


def main():
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.environ.setdefault(
        "ALPHAGSM_CONFIG_LOCATION",
        str(REPO_ROOT / "tests" / "alphagsm-test.conf"),
    )
    pyinstaller_run(
        [
            str(REPO_ROOT / "alphagsm"),
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "alphagsm",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
            "--specpath",
            str(BUILD_DIR),
            "--paths",
            str(REPO_ROOT / "src"),
            "--collect-submodules",
            "core",
            "--collect-submodules",
            "downloader",
            "--collect-submodules",
            "downloadermodules",
            "--collect-submodules",
            "gamemodules",
            "--collect-submodules",
            "screen",
            "--collect-submodules",
            "server",
            "--collect-submodules",
            "utils",
        ]
    )
    binary_name = "alphagsm.exe" if sys.platform.startswith("win") else "alphagsm"
    binary_path = DIST_DIR / binary_name
    if not binary_path.exists():
        raise SystemExit(f"Expected binary was not produced: {binary_path}")
    print(binary_path)


if __name__ == "__main__":
    main()