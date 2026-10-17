"""Explicit file-only acquisition using declared SteamCMD sources and recipes."""

import os
from pathlib import Path
import re
import shutil
import tempfile

from server.errors import ServerError
from utils import asset_import, byo_files, steamcmd


def acquire(server, recipe, source_id, *, auth_profile=None):
    """Download to scratch, validate declared content and import allowed files."""
    byo_files.require_managed_import(recipe)
    source = next((item for item in recipe.get("sources", []) if item.get("id") == source_id), None)
    if source is None:
        raise ServerError("Unknown BYO acquisition source; inspect assets requirements")
    if source.get("kind") != "steamcmd":
        raise ServerError("This source requires manual acquisition: " + source.get("instructions", "See the server guide"))
    app_ids = _declared_app_ids(source)
    platform = source.get("platform")
    branch = source.get("branch")
    if (any(not _valid_app_id(app_id) for app_id in app_ids)
            or platform not in {"linux", "windows", "macos"}
            or (branch is not None and not re.fullmatch(r"[A-Za-z0-9_.-]+", str(branch)))):
        raise ServerError("Invalid declared SteamCMD app, platform or branch")
    authentication = source.get("authentication")
    if authentication not in {"required", "anonymous"}:
        raise ServerError("Invalid declared SteamCMD authentication policy")
    if authentication == "required" and not auth_profile:
        raise ServerError("This source requires --auth-profile NAME with an entitled SteamCMD session")
    if not server.data.get("dir"):
        raise ServerError("Configure an installation directory with setup before acquiring files")
    target = Path(server.data["dir"]).absolute()
    scratch_parent = target.parent
    while not scratch_parent.exists():
        scratch_parent = scratch_parent.parent
    try:
        with tempfile.TemporaryDirectory(prefix=".alphagsm-byo-", dir=scratch_parent) as scratch:
            try:
                content_root = _download_declared_apps(
                    scratch, app_ids, authentication == "anonymous",
                    platform=platform, branch=branch, auth_profile=auth_profile,
                )
            except (RuntimeError, OSError):
                raise ServerError("SteamCMD file acquisition failed; check session and entitlement") from None
            # SteamCMD installs into the requested root. Validate before publication;
            # no source file or importer ownership metadata reaches the server yet.
            inspection = byo_files.inspect_files(content_root, recipe, source=True)
            if not inspection["ready"]:
                raise ServerError("Downloaded content lacks required files: " + ", ".join(inspection["missing"]))
            report = asset_import.import_assets(content_root, target, recipe)
            byo_files.assert_multiplayer_maps_retained(content_root, target)
    except OSError:
        raise ServerError("Unable to create or clean up BYO acquisition staging") from None
    report.update(source=source_id, game_readiness="not-checked", download_scope="app-or-depot")
    return report


def _valid_app_id(app_id):
    """Return whether one declared Steam app id is a safe decimal value."""

    return bool(re.fullmatch(r"[0-9]{1,10}", str(app_id))) and 0 < int(app_id) < 2**32


def _declared_app_ids(source):
    """Return the primary app id followed by any extra owned apps, in order."""

    extra = source.get("additional_app_ids") or []
    if isinstance(extra, str) or not isinstance(extra, (list, tuple)):
        raise ServerError("Invalid declared SteamCMD app, platform or branch")
    return [str(source.get("app_id", "")), *[str(app_id) for app_id in extra]]


def _download_declared_apps(scratch, app_ids, anonymous, *, platform, branch, auth_profile):
    """Download one or more owned apps without letting a later app delete an earlier one."""

    if len(app_ids) == 1:
        steamcmd.download(
            scratch, int(app_ids[0]), anonymous,
            force_platform=platform, beta_branch=branch, auth_profile=auth_profile,
        )
        return scratch
    content_root = os.path.join(scratch, "merged")
    os.makedirs(content_root)
    for app_id in app_ids:
        app_dir = os.path.join(scratch, "app-" + app_id)
        os.makedirs(app_dir)
        steamcmd.download(
            app_dir, int(app_id), anonymous,
            force_platform=platform, beta_branch=branch, auth_profile=auth_profile,
        )
        _merge_app_tree(app_dir, content_root)
    return content_root


def _merge_app_tree(app_dir, content_root):
    """Copy one Steam app into the shared content root. A later app replaces overlaps."""

    for dirpath, dirnames, filenames in os.walk(app_dir):
        dirnames[:] = [name for name in dirnames if name.lower() != "steamapps"]
        for name in filenames:
            source = os.path.join(dirpath, name)
            relative = os.path.relpath(source, app_dir)
            if relative == os.pardir or relative.startswith(os.pardir + os.sep):
                continue
            destination = os.path.join(content_root, relative)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
