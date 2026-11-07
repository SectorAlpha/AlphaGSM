"""Game-specific file guidance, owned imports and explicit source acquisition."""

import json

from server.errors import ServerError
from utils import asset_import, byo_acquire, byo_files, steam_auth, steam_library
from . import runtime


def recipe_for(server):
    """Read the selected module's public, credential-free asset declaration."""
    hook = getattr(server.module, "get_asset_requirements", None)
    if not callable(hook):
        raise ServerError("This module has no managed asset recipe; follow its server guide")
    return hook(server)


def _guard_stopped(server):
    """Require a configured, stopped instance before changing owned files."""
    if runtime.get_runtime(server).is_running(server):
        raise ServerError("The server must be stopped before importing or acquiring assets")
    if not server.data.get("dir"):
        raise ServerError("Configure an installation directory with setup before importing assets")


def import_for_setup(server, source):
    """Apply the stopped-server and recipe guards to setup and explicit imports."""
    recipe = recipe_for(server)
    _guard_stopped(server)
    byo_files.require_managed_import(recipe)
    return asset_import.import_assets(source, server.data["dir"], recipe)


def _steam_recipe_for(server):
    """Require one explicit Steam acquisition declaration on a managed recipe."""
    recipe = recipe_for(server)
    byo_files.require_managed_import(recipe)
    if recipe.get("managed_import") is not True:
        raise ServerError("Steam setup file selection requires an explicitly managed asset recipe")
    sources = [source for source in recipe.get("sources", []) if source.get("kind") == "steamcmd"]
    if len(sources) != 1:
        raise ServerError("This module requires exactly one declared SteamCMD source for setup file selection")
    return recipe, sources[0]


def validate_profile_reference(server, profile):
    """Validate only the profile identifier and recipe, without opening a cache."""
    try:
        steam_auth.validate_profile_name(profile)
    except steam_auth.SteamAuthError as error:
        raise ServerError(str(error)) from None
    return _steam_recipe_for(server)


def prepare_for_setup(server, *, assets_source=None, auth_profile=None, steam_dir=None):
    """Prepare selected owned files before engine installation; save names only."""
    if assets_source is not None:
        return import_for_setup(server, assets_source)
    if steam_dir is not None:
        recipe, source = _steam_recipe_for(server)
        _guard_stopped(server)
        installed = steam_library.find_installed_app(steam_dir, source.get("app_id"))
        return asset_import.import_assets(installed, server.data["dir"], recipe)
    if auth_profile is None and "steam_auth_profile" not in server.data:
        return None
    profile = auth_profile if auth_profile is not None else server.data["steam_auth_profile"]
    recipe, source = validate_profile_reference(server, profile)
    _guard_stopped(server)
    report = byo_files.inspect_files(byo_files.inspection_root(server, recipe), recipe)
    if not report["ready"]:
        report = byo_acquire.acquire(server, recipe, source["id"], auth_profile=profile)
    server.data["steam_auth_profile"] = profile
    server.data.save()
    return report


def _print_sources(recipe):
    """Explain acquisition without requesting or showing any credential values."""
    for item in recipe.get("sources", []):
        print(item["id"] + ": " + item["instructions"])
        if item.get("url"):
            print("  " + item["url"])


def execute(server, action, source=None, *, output=None, as_json=False, auth_profile=None):
    """Inspect recipes/files, import/export local content or explicitly acquire it."""
    recipe = recipe_for(server)
    if auth_profile is not None and action != "fetch":
        raise ServerError("--auth-profile is only valid with assets fetch")
    if action == "requirements" and source is None and output is None:
        report = recipe
    elif action == "check" and source is None and output is None:
        if "requirements" in recipe:
            report = byo_files.inspect_files(byo_files.inspection_root(server, recipe), recipe)
        else:
            if not server.data.get("dir"):
                raise ServerError("Configure an installation directory with setup before checking assets")
            report = asset_import.check_assets(server.data["dir"], recipe)
    elif action == "import" and source is not None and output is None:
        report = import_for_setup(server, source)
    elif action == "export" and source is not None and output is not None:
        byo_files.require_managed_import(recipe)
        report = asset_import.export_assets(source, output, recipe)
    elif action == "fetch" and source is not None and output is None:
        _guard_stopped(server)
        report = byo_acquire.acquire(server, recipe, source, auth_profile=auth_profile)
    else:
        raise ServerError("Use assets requirements/check, import PATH, export PATH --output ZIP, or fetch SOURCE --auth-profile NAME")
    if as_json:
        print(json.dumps(report, sort_keys=True))
    elif action == "requirements":
        print(recipe.get("description", "Required game files"))
        for item in recipe.get("requirements", []):
            print("  " + (item.get("path") or " or ".join(item["any_of"])))
        _print_sources(recipe)
        if recipe.get("managed_import") is False:
            print(recipe["manual_reason"])
    elif report.get("ready") is False:
        print("Assets missing: " + ", ".join(report["missing"]))
        _print_sources(recipe)
    elif action == "check":
        print("Declared files present; game readiness has not been checked")
    else:
        print("Assets ready" + (": " + report["output"] if "output" in report else ""))
    if report.get("ready") is False:
        raise ServerError("Required assets are missing; use assets requirements for file sources and staging instructions")
    return report
