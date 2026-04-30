"""Top-level AlphaGSM self-update helpers."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess as sp
import sys
import tempfile
import urllib.request

from utils.cmdparse import cmdparse
from utils.cmdparse.cmdspec import CmdSpec, OptSpec
from utils.github_releases import HTTP_USER_AGENT, read_json

from .version import REPO_ROOT, get_version


LATEST_RELEASE_API = "https://api.github.com/repos/SectorAlpha/AlphaGSM/releases/latest"
ALLOWED_GIT_UPDATE_BRANCHES = ("master", "main")
ALLOWED_GIT_UPDATE_PREFIXES = ("release",)

SELF_UPDATE_CMDSPEC = CmdSpec(
    options=(
        OptSpec(
            "c",
            ["check"],
            "Check whether an AlphaGSM update is available without applying it.",
            "check",
            None,
            True,
        ),
        OptSpec(
            "s",
            ["source"],
            "Update source to use: auto, git, or binary.",
            "source",
            "SOURCE",
            str,
        ),
    )
)

SELF_UPDATE_DESCRIPTION = (
    "Check for a newer AlphaGSM release and apply it when supported.\n"
    "Source checkouts use git fast-forward updates on tracked non-developer branches\n"
    "(master/main/release* only). Standalone binaries use the latest GitHub release asset\n"
    "for the current platform and architecture."
)


class SelfUpdateError(RuntimeError):
    """Raised when self-update cannot proceed safely."""


def run_self_update(name, args, *, stderr=None):
    """Parse and execute the top-level self-update command."""

    del name
    if stderr is None:
        stderr = sys.stderr
    try:
        parsed_args, opts = cmdparse.parse(args, SELF_UPDATE_CMDSPEC)
    except Exception as ex:
        print("Error parsing arguments and options", file=stderr)
        print(ex, file=stderr)
        print(file=stderr)
        cmdparse.longhelp("self-update", SELF_UPDATE_DESCRIPTION, SELF_UPDATE_CMDSPEC, file=stderr)
        return 2
    if parsed_args:
        print("self-update does not accept positional arguments", file=stderr)
        print(file=stderr)
        cmdparse.longhelp("self-update", SELF_UPDATE_DESCRIPTION, SELF_UPDATE_CMDSPEC, file=stderr)
        return 2

    check_only = bool(opts.get("check", False))
    source = str(opts.get("source", "auto")).strip().lower() or "auto"
    try:
        resolved_source = _detect_install_source() if source == "auto" else source
        if resolved_source == "git":
            return _run_git_self_update(check=check_only)
        if resolved_source == "binary":
            return _run_binary_self_update(check=check_only)
        raise SelfUpdateError("Unsupported self-update source: %s" % (resolved_source,))
    except SelfUpdateError as ex:
        print(ex, file=stderr)
        return 1


def _detect_install_source():
    """Infer whether AlphaGSM is running from git or a bundled binary."""

    if getattr(sys, "frozen", False):
        return "binary"
    if (REPO_ROOT / ".git").exists():
        return "git"
    raise SelfUpdateError(
        "Unable to determine how AlphaGSM was installed; specify --source explicitly."
    )


def _run_git_self_update(*, check=False):
    """Check for or apply a git-based self-update."""

    branch = _git_output(["rev-parse", "--abbrev-ref", "HEAD"])
    if branch == "HEAD":
        raise SelfUpdateError("Git self-update is unavailable from a detached HEAD checkout.")

    upstream_ref = _git_upstream_ref(branch)
    remote_name, remote_branch = upstream_ref.split("/", 1)
    _git_run(["fetch", remote_name, remote_branch])

    local_rev = _git_output(["rev-parse", "HEAD"])
    upstream_rev = _git_output(["rev-parse", upstream_ref])
    merge_base = _git_output(["merge-base", "HEAD", upstream_ref])

    print("Current version: %s" % (get_version(),))
    print("Git branch: %s" % (branch,))
    print("Tracking ref: %s" % (upstream_ref,))

    if local_rev == upstream_rev:
        print("No update available")
        return 0

    if upstream_rev == merge_base:
        print("Local checkout is already ahead of the tracked branch")
        return 0

    if local_rev != merge_base:
        raise SelfUpdateError(
            "Local checkout has diverged from %s; refusing automatic git self-update." % (upstream_ref,)
        )

    print("Update available")
    if check:
        return 0

    if not _is_git_update_branch_allowed(branch):
        raise SelfUpdateError(
            "Git self-update is disabled on developer branch '%s'. Switch to master/main or a release* branch first." % (branch,)
        )

    if _git_output(["status", "--porcelain"]):
        raise SelfUpdateError(
            "Working tree is dirty; commit or stash local changes before running self-update."
        )

    _git_run(["merge", "--ff-only", upstream_ref])
    print("Updated AlphaGSM to %s" % (_git_output(["rev-parse", "--short", "HEAD"]),))
    print("Restart AlphaGSM to use the updated codebase")
    return 0


def _is_git_update_branch_allowed(branch):
    """Return whether *branch* is eligible for automatic git self-update."""

    return branch in ALLOWED_GIT_UPDATE_BRANCHES or branch.startswith(ALLOWED_GIT_UPDATE_PREFIXES)


def _git_upstream_ref(branch):
    """Return the tracked upstream ref for *branch* or a safe origin fallback."""

    try:
        return _git_output(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    except SelfUpdateError:
        fallback = "origin/%s" % (branch,)
        _git_run(["fetch", "origin", branch])
        return fallback


def _git_output(args):
    """Run a git command and return stripped stdout."""

    try:
        return sp.check_output(["git"] + list(args), cwd=str(REPO_ROOT), stderr=sp.DEVNULL, text=True).strip()
    except (OSError, sp.CalledProcessError) as ex:
        raise SelfUpdateError("Git command failed: git %s" % (" ".join(args),)) from ex


def _git_run(args):
    """Run a git command and raise a user-facing error if it fails."""

    try:
        sp.check_call(["git"] + list(args), cwd=str(REPO_ROOT))
    except (OSError, sp.CalledProcessError) as ex:
        raise SelfUpdateError("Git command failed: git %s" % (" ".join(args),)) from ex


def _run_binary_self_update(*, check=False):
    """Check for or apply a bundled-binary self-update."""

    release_data = read_json(LATEST_RELEASE_API)
    latest_version = _normalize_release_version(release_data.get("tag_name", ""))
    current_version = _normalize_release_version(get_version())

    if not latest_version:
        raise SelfUpdateError("Latest release metadata did not include a version tag.")

    print("Current version: %s" % (current_version or "unknown",))
    print("Latest version: %s" % (latest_version,))

    if not _is_newer_version(latest_version, current_version):
        print("No update available")
        return 0

    print("Update available")
    if check:
        return 0

    if os.name == "nt":
        raise SelfUpdateError(
            "Binary self-update is not supported while running on Windows; replace the executable manually."
        )

    binary_asset, checksum_asset = _select_release_assets(release_data, latest_version)
    _replace_current_binary(binary_asset["browser_download_url"], checksum_asset["browser_download_url"])
    print("Updated AlphaGSM binary to %s" % (latest_version,))
    print("Restart AlphaGSM to use the new binary")
    return 0


def _select_release_assets(release_data, latest_version):
    """Select the binary and checksum assets for the current platform."""

    platform_slug = _platform_slug()
    arch_slug = _arch_slug()
    expected_prefix = "alphagsm-%s-%s-%s" % (latest_version, platform_slug, arch_slug)
    binary_asset = None
    checksum_asset = None
    for asset in release_data.get("assets", []):
        name = str(asset.get("name", ""))
        if name == expected_prefix or name == expected_prefix + ".exe":
            binary_asset = asset
        elif name == expected_prefix + ".sha256" or name == expected_prefix + ".exe.sha256":
            checksum_asset = asset
    if binary_asset is None or checksum_asset is None:
        raise SelfUpdateError(
            "Unable to locate release assets for %s/%s in the latest GitHub release." % (platform_slug, arch_slug)
        )
    return binary_asset, checksum_asset


def _replace_current_binary(binary_url, checksum_url):
    """Download, verify, and atomically replace the current executable."""

    current_path = Path(sys.executable).resolve()
    if not current_path.exists():
        raise SelfUpdateError("Current executable path does not exist: %s" % (current_path,))

    with tempfile.TemporaryDirectory(prefix="alphagsm-self-update-") as temp_dir:
        temp_dir = Path(temp_dir)
        downloaded_binary = temp_dir / current_path.name
        downloaded_checksum = temp_dir / (current_path.name + ".sha256")
        _download(binary_url, downloaded_binary)
        _download(checksum_url, downloaded_checksum)
        _verify_checksum(downloaded_binary, downloaded_checksum)
        current_mode = stat.S_IMODE(current_path.stat().st_mode)
        os.chmod(downloaded_binary, current_mode)
        replacement_path = current_path.with_name(current_path.name + ".new")
        os.replace(downloaded_binary, replacement_path)
        os.replace(replacement_path, current_path)


def _download(url, target_path):
    """Download *url* to *target_path* using AlphaGSM's HTTP user agent."""

    request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response, open(target_path, "wb") as handle:
        handle.write(response.read())


def _verify_checksum(binary_path, checksum_path):
    """Verify a staged binary against its release checksum sidecar."""

    checksum_line = checksum_path.read_text(encoding="utf-8").strip()
    expected_hash = checksum_line.split()[0] if checksum_line else ""
    actual_hash = hashlib.sha256(binary_path.read_bytes()).hexdigest()
    if not expected_hash or actual_hash != expected_hash:
        raise SelfUpdateError("Downloaded binary failed SHA256 verification.")


def _platform_slug():
    """Return the release workflow's platform slug for this runtime."""

    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    raise SelfUpdateError("Unsupported platform for binary self-update: %s" % (sys.platform,))


def _arch_slug():
    """Return the release workflow's architecture slug for this runtime."""

    machine = (os.environ.get("PROCESSOR_ARCHITECTURE") or os.uname().machine).lower()
    if machine in ("x86_64", "amd64"):
        return "X64"
    if machine in ("aarch64", "arm64"):
        return "ARM64"
    raise SelfUpdateError("Unsupported architecture for binary self-update: %s" % (machine,))


def _normalize_release_version(version):
    """Normalize git tag or release version strings for display and comparison."""

    version = str(version or "").strip()
    return version[1:] if version.startswith("v") else version


def _is_newer_version(latest_version, current_version):
    """Return whether *latest_version* is newer than *current_version*."""

    latest_version = _normalize_release_version(latest_version)
    current_version = _normalize_release_version(current_version)
    if not latest_version:
        return False
    if not current_version:
        return True
    if latest_version == current_version:
        return False
    return _version_key(latest_version) > _version_key(current_version)


def _version_key(version):
    """Return a simple comparable key for release-like version strings."""

    tokens = re.findall(r"\d+|[A-Za-z]+", _normalize_release_version(version))
    return tuple((0, int(token)) if token.isdigit() else (1, token.lower()) for token in tokens)