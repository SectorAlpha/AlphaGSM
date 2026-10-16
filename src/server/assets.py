"""Shared operator-owned asset commands for modules with an asset recipe."""

import json

from server.errors import ServerError
from utils import asset_import
from . import runtime


def recipe_for(server):
    hook = getattr(server.module, "get_asset_requirements", None)
    if not callable(hook):
        raise ServerError("This module has no managed asset import recipe; follow its server guide")
    return hook(server)


def import_for_setup(server, source):
    """Apply the same stopped-server guard to setup imports and explicit imports."""
    recipe = recipe_for(server)
    if runtime.get_runtime(server).is_running(server):
        raise ServerError("The server must be stopped before importing assets")
    if not server.data.get("dir"):
        raise ServerError("Configure an installation directory with setup before importing assets")
    return asset_import.import_assets(source, server.data["dir"], recipe)


def execute(server, action, source=None, *, output=None, as_json=False):
    """Inspect/import owned assets or create a portable ZIP from a local source."""
    recipe = recipe_for(server)
    if action == "check" and source is None and output is None:
        if not server.data.get("dir"):
            raise ServerError("Configure an installation directory with setup before checking assets")
        report = asset_import.check_assets(server.data["dir"], recipe)
    elif action == "import" and source is not None and output is None:
        report = import_for_setup(server, source)
    elif action == "export" and source is not None and output is not None:
        report = asset_import.export_assets(source, output, recipe)
    else:
        raise ServerError("Use assets check, assets import PATH, or assets export PATH --output ZIP")
    if as_json:
        print(json.dumps(report, sort_keys=True))
    elif report.get("ready") is False:
        print("Assets missing: " + ", ".join(report["missing"]))
    else:
        print("Assets ready" + (": " + report["output"] if "output" in report else ""))
    if report.get("ready") is False:
        raise ServerError("Required assets are missing; use assets import PATH or setup --assets PATH")
    return report
