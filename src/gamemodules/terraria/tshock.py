"""TShock server module for Terraria."""

import hashlib
from pathlib import Path
import shutil
from urllib.parse import urlparse

import server.runtime as runtime_module
from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_zip_safe,
    install_staged_tree,
    stage_single_file,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.reconcile import reconcile_mod_state
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

from .common import (
    backup,
    checkvalue,
    command_args,
    command_descriptions,
    command_functions,
    commands,
    configure_base,
    do_stop,
    get_tshock_start_command,
    install_archive,
    message,
    resolve_tshock_download,
    setting_schema,
    status,
)
from utils.gamemodules import common as gamemodule_common


commands = commands + ("mod",)
command_args = command_args.copy()
command_descriptions = command_descriptions.copy()
command_functions = command_functions.copy()

ALLOWED_TSHOCK_MOD_DESTINATIONS = ("ServerPlugins", "tshock")
TSHOCK_MOD_CACHE_DIRNAME = "terraria-tshock"

command_args["mod"] = CmdSpec(
    requiredarguments=(ArgSpec("ACTION", "mod action", str),),
    optionalarguments=(
        ArgSpec("SOURCE", "url", str),
        ArgSpec("IDENTIFIER", "plugin URL", str),
        ArgSpec("EXTRA", "optional plugin filename", str),
    ),
)
command_descriptions["mod"] = "Manage TShock plugins from direct download URLs."


def ensure_mod_state(server):
    """Seed the TShock plugin datastore shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("url", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
    mods.setdefault("errors", [])
    return mods


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / TSHOCK_MOD_CACHE_DIRNAME


def _resolve_plugin_url(url: str, filename: str | None = None) -> dict:
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ServerError("TShock mod url entries require an http or https URL")

    resolved_filename = filename or Path(parsed.path).name
    if not resolved_filename or not (
        resolved_filename.endswith(".dll") or resolved_filename.endswith(".zip")
    ):
        raise ServerError("TShock mod url entries require a plugin .dll or .zip filename")

    digest = hashlib.sha256(str(url).encode("utf-8")).hexdigest()[:12]
    archive_type = "zip" if resolved_filename.endswith(".zip") else "dll"
    return {
        "source_type": "url",
        "requested_id": str(url),
        "resolved_id": f"url.{digest}.{resolved_filename}",
        "download_url": str(url),
        "filename": resolved_filename,
        "allowed_host": parsed.hostname,
        "archive_type": archive_type,
    }


def _reject_duplicate_url_entry(mods, requested_id):
    for entry in mods["desired"]["url"]:
        if entry.get("requested_id") == requested_id:
            raise ServerError(f"TShock mod '{requested_id}' is already present in desired state")


def _desired_entries(server) -> list[DesiredModEntry]:
    return [
        DesiredModEntry(
            source_type="url",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in ensure_mod_state(server)["desired"]["url"]
    ]


def _installed_entries(server) -> list[InstalledModEntry]:
    return [
        InstalledModEntry(
            source_type=entry["source_type"],
            resolved_id=entry["resolved_id"],
            installed_files=list(entry.get("installed_files", [])),
        )
        for entry in ensure_mod_state(server).get("installed", [])
    ]


def _serialize_installed_entries(entries: list[InstalledModEntry]) -> list[dict]:
    return [
        {
            "source_type": entry.source_type,
            "resolved_id": entry.resolved_id,
            "installed_files": list(entry.installed_files),
        }
        for entry in entries
    ]


def _desired_record(server, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"]["url"]:
        if entry.get("resolved_id") == resolved_id:
            return entry
    raise ModSupportError(f"Missing desired-state metadata for TShock plugin '{resolved_id}'")


def _install_url_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    desired_record = _desired_record(server, desired_entry.resolved_id)
    cache_root = _cache_root(server) / "url"
    cache_root.mkdir(parents=True, exist_ok=True)
    archive_path = cache_root / desired_record["filename"]
    download_to_cache(
        desired_record["download_url"],
        allowed_hosts=(desired_record["allowed_host"],),
        target_path=archive_path,
    )
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    if desired_record["archive_type"] == "zip":
        extract_zip_safe(archive_path, stage_root)
    else:
        stage_single_file(archive_path, stage_root, f"ServerPlugins/{desired_record['filename']}")

    server_root = Path(server.data["dir"])
    installed_paths = install_staged_tree(
        staged_root=stage_root,
        server_root=server_root,
        allowed_destinations=ALLOWED_TSHOCK_MOD_DESTINATIONS,
    )
    return InstalledModEntry(
        source_type="url",
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(server_root, installed_paths),
    )


def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    if desired_entry.source_type == "url":
        return _install_url_entry(server, desired_entry)
    raise ModSupportError(f"Unsupported TShock mod source: {desired_entry.source_type}")


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"])
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current != server_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def cleanup_configured_mods(server):
    """Remove installed TShock plugin files and reset tracked plugin state."""

    mods = ensure_mod_state(server)
    for installed_entry in _installed_entries(server):
        _remove_owned_entry(server, installed_entry)
    shutil.rmtree(_cache_root(server), ignore_errors=True)
    mods["desired"] = {"url": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    server.data.save()


def apply_configured_mods(server):
    """Reconcile configured TShock plugins into the server install."""

    mods = ensure_mod_state(server)
    if not mods.get("enabled", True):
        return
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_entry(server, entry),
            remove_entry=lambda entry: _remove_owned_entry(server, entry),
        )
    except (ModSupportError, ServerError) as exc:
        mods["errors"] = [str(exc)]
        server.data.save()
        if isinstance(exc, ServerError):
            raise
        raise ServerError(str(exc)) from exc
    mods["installed"] = _serialize_installed_entries(reconciled)
    mods["last_apply"] = "success"
    mods["errors"] = []
    server.data.save()


def tshock_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the TShock ``mod`` command desired-state subcommands."""

    del kwargs
    mods = ensure_mod_state(server)
    if action == "list":
        print(mods)
        return
    if action == "apply":
        apply_configured_mods(server)
        return
    if action == "cleanup":
        cleanup_configured_mods(server)
        return
    if action == "add" and source == "url":
        if not identifier:
            raise ServerError("TShock mod add url requires a plugin URL")
        resolved = _resolve_plugin_url(identifier, extra)
        _reject_duplicate_url_entry(mods, resolved["requested_id"])
        mods["desired"]["url"].append(resolved)
        server.data.save()
        return
    raise ServerError("Unsupported TShock mod command")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="TShock.Server.dll",
    download_name="tshock.zip"
):
    """Collect and store configuration values for a TShock server."""

    if url is None:
        version, url = resolve_tshock_download()
    result = configure_base(
        server,
        ask,
        port,
        dir,
        exe_name=exe_name,
        version=version,
        url=url,
        download_name=download_name,
        max_players=8,
        world_name=server.name,
        world_size=2,
        backupfiles=("Worlds", "serverconfig.txt", "tshock"),
        java_runtime="dotnet",
    )
    ensure_mod_state(server)
    return result


def install(server):
    """Download and install the TShock server files."""

    install_archive(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def get_start_command(server):
    """Build the start command for TShock."""

    return get_tshock_start_command(server)


command_functions["mod"] = tshock_mod_command

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
