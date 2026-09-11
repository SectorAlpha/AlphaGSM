"""Version helpers for AlphaGSM CLI and binary builds."""

from __future__ import annotations

import os
import subprocess as sp
from pathlib import Path

from ._build_version import VERSION as BUILD_VERSION


REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_describe_version():
    """Return a best-effort git-derived version string when available."""

    git_dir = REPO_ROOT / ".git"
    if not git_dir.exists():
        return None
    try:
        version = sp.check_output(
            ["git", "describe", "--tags", "--dirty", "--always"],
            cwd=str(REPO_ROOT),
            stderr=sp.DEVNULL,
            text=True,
        ).strip()
    except (OSError, sp.SubprocessError):
        return None
    if not version:
        return None
    return version[1:] if version.startswith("v") else version


def get_version():
    """Return the current AlphaGSM version string."""

    env_version = os.environ.get("ALPHAGSM_VERSION", "").strip()
    if env_version:
        return env_version
    git_version = _git_describe_version()
    if git_version:
        return git_version
    return BUILD_VERSION