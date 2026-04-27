#!/usr/bin/env python3
"""Build a standalone AlphaGSM binary with PyInstaller."""

import argparse
import hashlib
from pathlib import Path
import os
import shutil
import subprocess as sp
import sys

from PyInstaller.__main__ import run as pyinstaller_run


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = REPO_ROOT / "dist-binary"
BUILD_DIR = REPO_ROOT / "build" / "pyinstaller"
BUILD_VERSION_FILE = REPO_ROOT / "src" / "core" / "_build_version.py"


def parse_args():
    """Parse command-line options for the binary builder."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version",
        help="Version string to stamp into the build and release artifacts.",
    )
    parser.add_argument(
        "--release-dir",
        help="Optional directory where renamed release artifacts and checksums are staged.",
    )
    parser.add_argument(
        "--artifact-name",
        help="Optional basename to use when staging the release artifact.",
    )
    return parser.parse_args()


def _git_describe_version():
    """Return a best-effort git-derived version string."""

    try:
        version = sp.check_output(
            ["git", "describe", "--tags", "--dirty", "--always"],
            cwd=str(REPO_ROOT),
            stderr=sp.DEVNULL,
            text=True,
        ).strip()
    except (OSError, sp.SubprocessError):
        return ""
    if version.startswith("v"):
        version = version[1:]
    return version


def resolve_version(requested_version=None):
    """Resolve the build version from args, env, git, or the development fallback."""

    for candidate in (
        requested_version,
        os.environ.get("ALPHAGSM_VERSION"),
        _git_describe_version(),
        "0.0.0-dev",
    ):
        value = str(candidate or "").strip()
        if value:
            return value
    return "0.0.0-dev"


def write_build_version(version):
    """Write the generated build-version module used by the CLI."""

    BUILD_VERSION_FILE.write_text(
        '"""Generated build version for AlphaGSM."""\n\nVERSION = %r\n' % (version,),
        encoding="utf-8",
    )


def write_sha256(path):
    """Write a standard sha256 sidecar file for *path*."""

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    checksum_path = path.with_name(path.name + ".sha256")
    checksum_path.write_text("%s  %s\n" % (digest, path.name), encoding="utf-8")
    return checksum_path


def stage_release_artifact(binary_path, release_dir, artifact_name=None):
    """Copy *binary_path* into *release_dir* and emit a checksum sidecar."""

    release_dir = Path(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    suffix = binary_path.suffix
    target_name = artifact_name or binary_path.stem
    staged_binary = release_dir / (target_name + suffix)
    shutil.copy2(binary_path, staged_binary)
    checksum_path = write_sha256(staged_binary)
    return staged_binary, checksum_path


def main():
    args = parse_args()
    version = resolve_version(args.version)
    previous_build_version = BUILD_VERSION_FILE.read_text(encoding="utf-8")

    shutil.rmtree(DIST_DIR, ignore_errors=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.environ.setdefault(
        "ALPHAGSM_CONFIG_LOCATION",
        str(REPO_ROOT / "tests" / "alphagsm-test.conf"),
    )

    try:
        write_build_version(version)
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
        checksum_path = write_sha256(binary_path)
        if args.release_dir:
            binary_path, checksum_path = stage_release_artifact(
                binary_path,
                args.release_dir,
                artifact_name=args.artifact_name,
            )
        print(binary_path)
        print(checksum_path)
    finally:
        BUILD_VERSION_FILE.write_text(previous_build_version, encoding="utf-8")


if __name__ == "__main__":
    main()