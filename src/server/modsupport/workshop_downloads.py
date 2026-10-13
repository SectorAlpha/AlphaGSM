"""Validated anonymous Workshop downloads shared by SteamCMD game servers."""

import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

from server.errors import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils import steamcmd
from . import workshop
from .downloads import install_staged_tree
from .errors import ModSupportError

COMMAND_SPEC = CmdSpec(
    requiredarguments=(ArgSpec("ACTION", "download or list", str),),
    optionalarguments=(
        ArgSpec("SOURCE", "item or collection", str),
        ArgSpec("IDENTIFIER", "Workshop ID or Steam Community URL", str),
    ),
)
COMMAND_DESCRIPTION = (
    "Download game-validated Workshop items or collections with anonymous SteamCMD login. "
    "Files are staged per server; use the game's installation rules to activate them."
)


def supports_anonymous_workshop(server):
    """Use module-owned Steam metadata, never an editable datastore auth flag."""
    module = server.module
    family = getattr(module, "MODULE", None)
    anonymous = getattr(module, "steam_anonymous_login_possible", None)
    if anonymous is None:
        anonymous = getattr(family, "steam_anonymous_login_possible", None)
    app_id = getattr(module, "steam_app_id", getattr(family, "steam_app_id", None))
    return anonymous is True and app_id is not None


def _app_id(value):
    """Validate a game AppID independently from a dedicated-server tool ID."""
    text = workshop.validate_workshop_identifier(value)
    if int(text) >= 2**32:
        raise ModSupportError("Steam Workshop game AppID must fit uint32")
    return int(text)


def _server_root(server):
    """Require a configured installation before staging server-owned downloads."""
    directory = server.data.get("dir")
    if not directory or not Path(directory).is_dir():
        raise ServerError("Run server setup before downloading Workshop content")
    return Path(directory).resolve()


def _source_app_id(server, root):
    """Read the configured Source game's identity without scanning mounted games."""
    game_dir = server.data.get("game_dir")
    if not game_dir:
        return None
    path = root / game_dir / "gameinfo.txt"
    _check_managed_path(root, path)
    if not path.is_file():
        return None
    with path.open(encoding="utf-8-sig") as handle:
        raw = handle.read(128 * 1024 + 1)
    if len(raw) > 128 * 1024:
        raise ServerError("Installed gameinfo.txt exceeds the size limit")
    tokens = [token for token in re.findall(r'//[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+', raw)
              if not token.startswith("//")]
    app_ids = {_app_id(tokens[index + 1].strip('"')) for index, token in enumerate(tokens[:-1])
               if token.strip('"').lower() == "steamappid"}
    if len(app_ids) > 1:
        raise ServerError("Installed gameinfo.txt has conflicting game AppIDs")
    return app_ids.pop() if app_ids else None


def resolve_server_workshop_app_id(server):
    """Read explicit module identity or Valve's installed game AppID file."""
    explicit = getattr(server.module, "workshop_app_id", None)
    if explicit is not None:
        return _app_id(explicit)
    root = _server_root(server)
    source_app_id = _source_app_id(server, root)
    if source_app_id is not None:
        return source_app_id
    app_ids = set()
    for index, (directory, subdirectories, filenames) in enumerate(os.walk(root, followlinks=False)):
        if index >= 4096:
            raise ServerError("Installed game AppID search exceeds the directory limit")
        subdirectories[:] = [name for name in subdirectories
                             if name.lower() not in ("workshop", "mods", ".alphagsm", "_gmod_content")]
        if "steam_appid.txt" not in filenames:
            continue
        path = Path(directory) / "steam_appid.txt"
        if path.is_symlink():
            raise ServerError("Refusing symlinked installed game AppID file")
        with path.open(encoding="utf-8-sig") as handle:
            value = handle.read(33)
        if len(value) > 32:
            raise ServerError("Installed game AppID file exceeds the size limit")
        app_ids.add(_app_id(value.strip()))
    if len(app_ids) > 1:
        raise ServerError("Installed steam_appid.txt files have conflicting game AppIDs")
    if not app_ids:
        raise ServerError(
            "Cannot verify the Workshop game AppID: the module needs workshop_app_id "
            "or upstream server files need steam_appid.txt containing the game's AppID"
        )
    return app_ids.pop()


def _check_managed_path(root, destination):
    """Reject escaping paths and symlink ancestors before download or copying."""
    try:
        destination.resolve().relative_to(root)
    except ValueError as exc:
        raise ServerError("Workshop staging destination is outside server root") from exc
    current = destination
    while current != root:
        if current.is_symlink():
            raise ServerError("Refusing Workshop staging through a symlink")
        current = current.parent


def _check_cache(root, cache):
    """Reject symlinked cache files and directories before SteamCMD can write."""
    _check_managed_path(root, cache)
    for directory, subdirectories, filenames in os.walk(cache, followlinks=False):
        for name in subdirectories + filenames:
            if (Path(directory) / name).is_symlink():
                raise ServerError("Refusing Workshop download through a symlinked cache")


def _publish_download(root, managed_root, downloaded, destination):
    """Replace staged content with a fresh payload, restoring it on publish failure."""
    managed_root.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".stage-", dir=managed_root) as temporary:
        fresh = Path(temporary) / "payload"
        install_staged_tree(staged_root=downloaded, server_root=fresh, allowed_destinations=(".",))
        _check_managed_path(root, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        previous = managed_root / f".previous-{uuid4().hex}"
        if destination.exists():
            if not destination.is_dir():
                raise ServerError("Workshop staging destination must be a directory")
            destination.rename(previous)
        try:
            fresh.rename(destination)
        except OSError:
            if previous.exists():
                try:
                    previous.rename(destination)
                except OSError as exc:
                    raise ServerError(f"Workshop refresh failed; previous payload retained at {previous}") from exc
            raise
        if previous.exists():
            shutil.rmtree(previous)


def run_workshop_command(server, action, source=None, identifier=None):
    """Stage validated content without assuming engine-specific activation rules."""
    if not supports_anonymous_workshop(server):
        raise ServerError("Workshop downloads require an anonymous SteamCMD server module")
    if action == "list":
        print(server.data.get("workshop_downloads", {"items": []}))
        return
    if action != "download" or source not in ("item", "collection") or identifier is None:
        raise ServerError("Use workshop download item|collection ID_OR_URL, or workshop list")
    state = None
    try:
        identifier = workshop.normalize_workshop_identifier(identifier)
        root = _server_root(server)
        app_id = resolve_server_workshop_app_id(server)
        managed_root = root / ".alphagsm" / "workshop"
        _check_managed_path(root, managed_root)
        cache = managed_root / "cache"
        _check_cache(root, cache)
        if source == "collection":
            item_ids = workshop.resolve_workshop_collection(identifier, app_id)
        else:
            item_ids = [workshop.resolve_workshop_item(identifier, app_id)["workshop_id"]]
        # Preflight every destination before a collection can trigger any downloads.
        for item_id in item_ids:
            _check_managed_path(root, managed_root / "content" / str(app_id) / item_id)
        state = server.data.setdefault("workshop_downloads", {"items": [], "errors": []})
        for item_id in item_ids:
            _check_cache(root, cache)
            downloaded = steamcmd.download_workshop_item(cache, app_id, item_id, True)
            destination = managed_root / "content" / str(app_id) / item_id
            _publish_download(root, managed_root, downloaded, destination)
            state["items"] = [entry for entry in state["items"]
                              if (entry["app_id"], entry["workshop_id"]) != (app_id, item_id)]
            state["items"].append({"app_id": app_id, "workshop_id": item_id,
                                   "path": destination.relative_to(root).as_posix()})
            state["errors"] = []
            server.data.save()
            print(f"Downloaded Workshop item {item_id} to {destination}")
    except (ModSupportError, ServerError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        message = getattr(exc, "output", None) or str(exc)
        if state is not None:
            state["errors"] = [message]
            server.data.save()
        raise ServerError(str(message)) from exc
