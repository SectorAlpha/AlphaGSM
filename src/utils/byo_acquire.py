"""Explicit file-only acquisition using declared SteamCMD sources and recipes."""

from pathlib import Path
import re
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
    app_id = str(source.get("app_id", ""))
    platform = source.get("platform")
    branch = source.get("branch")
    if (not re.fullmatch(r"[0-9]{1,10}", app_id) or not 0 < int(app_id) < 2**32
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
                steamcmd.download(scratch, int(app_id), authentication == "anonymous",
                                  force_platform=platform, beta_branch=branch, auth_profile=auth_profile)
            except (RuntimeError, OSError):
                raise ServerError("SteamCMD file acquisition failed; check session and entitlement") from None
            # SteamCMD installs into the requested root. Validate before publication;
            # no source file or importer ownership metadata reaches the server yet.
            inspection = byo_files.inspect_files(scratch, recipe, source=True)
            if not inspection["ready"]:
                raise ServerError("Downloaded content lacks required files: " + ", ".join(inspection["missing"]))
            report = asset_import.import_assets(scratch, target, recipe)
    except OSError:
        raise ServerError("Unable to create or clean up BYO acquisition staging") from None
    report.update(source=source_id, game_readiness="not-checked", download_scope="app-or-depot")
    return report
