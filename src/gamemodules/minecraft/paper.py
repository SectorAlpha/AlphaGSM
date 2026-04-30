"""PaperMC-specific setup and install helpers."""

import hashlib
from pathlib import Path
import shutil
from urllib.parse import urlparse

from .custom import *
from . import custom as cust
from .papermc import resolve_download
from server import ServerError
from server.modsupport.downloads import download_to_cache, install_staged_tree, stage_single_file
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.reconcile import reconcile_mod_state
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules.minecraft.jardownload import install_downloaded_jar


import server.runtime as runtime_module

commands = commands + ("mod",)
command_args = command_args.copy()
command_descriptions = command_descriptions.copy()
command_functions = command_functions.copy()

ALLOWED_PAPER_PLUGIN_DESTINATIONS = ("plugins",)
PAPER_MOD_CACHE_DIRNAME = "minecraft-paper"

command_args["setup"] = command_args["setup"].combine(
    CmdSpec(
        options=(
            OptSpec(
                "v",
                ["version"],
                "Minecraft version to download. Uses the latest stable build by default.",
                "version",
                "VERSION",
                str,
            ),
            OptSpec(
                "u",
                ["url"],
                "Download URL to use instead of the PaperMC downloads service.",
                "url",
                "URL",
                str,
            ),
        )
    )
)
command_args["mod"] = CmdSpec(
    requiredarguments=(ArgSpec("ACTION", "mod action", str),),
    optionalarguments=(
        ArgSpec("SOURCE", "url", str),
        ArgSpec("IDENTIFIER", "plugin jar url", str),
        ArgSpec("EXTRA", "optional plugin filename", str),
    ),
)
command_descriptions["mod"] = "Manage Paper plugin jars from direct download URLs."


def ensure_mod_state(server):
    """Seed the Paper plugin datastore shape and return it."""

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
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / PAPER_MOD_CACHE_DIRNAME


def _resolve_plugin_url(url: str, filename: str | None = None) -> dict:
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ServerError("Paper mod url entries require an http or https URL")

    resolved_filename = filename or Path(parsed.path).name
    if not resolved_filename or not resolved_filename.endswith(".jar"):
        raise ServerError("Paper mod url entries require a plugin .jar filename")

    digest = hashlib.sha256(str(url).encode("utf-8")).hexdigest()[:12]
    return {
        "source_type": "url",
        "requested_id": str(url),
        "resolved_id": f"url.{digest}.{resolved_filename}",
        "download_url": str(url),
        "filename": resolved_filename,
        "allowed_host": parsed.hostname,
    }


def _reject_duplicate_url_entry(mods, requested_id):
    for entry in mods["desired"]["url"]:
        if entry.get("requested_id") == requested_id:
            raise ServerError(f"Paper mod '{requested_id}' is already present in desired state")


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
    raise ModSupportError(f"Missing desired-state metadata for Paper plugin '{resolved_id}'")


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
    stage_single_file(archive_path, stage_root, f"plugins/{desired_record['filename']}")
    server_root = Path(server.data["dir"])
    installed_paths = install_staged_tree(
        staged_root=stage_root,
        server_root=server_root,
        allowed_destinations=ALLOWED_PAPER_PLUGIN_DESTINATIONS,
    )
    return InstalledModEntry(
        source_type="url",
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(server_root, installed_paths),
    )


def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    if desired_entry.source_type == "url":
        return _install_url_entry(server, desired_entry)
    raise ModSupportError(f"Unsupported Paper mod source: {desired_entry.source_type}")


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
    """Remove installed Paper plugin files and reset tracked plugin state."""

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
    """Reconcile configured Paper plugins into the plugins directory."""

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


def paper_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the Paper ``mod`` command desired-state subcommands."""

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
            raise ServerError("Paper mod add url requires a plugin jar URL")
        resolved = _resolve_plugin_url(identifier, extra)
        _reject_duplicate_url_entry(mods, resolved["requested_id"])
        mods["desired"]["url"].append(resolved)
        server.data.save()
        return
    raise ServerError("Unsupported Paper mod command")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    eula=None,
    version=None,
    url=None,
    exe_name="paper.jar",
    download_name="paper.jar"
):
    """Collect configuration values for a PaperMC server."""

    if url is None:
        resolved_version, url = resolve_download("paper", version=version)
        server.data["version"] = resolved_version
    else:
        server.data["version"] = version
    server.data["url"] = url
    server.data["download_name"] = download_name
    result = cust.configure(server, ask, port, dir, eula=eula, exe_name=exe_name)
    ensure_mod_state(server)
    return result


def install(server, *, eula=False):
    """Download or validate the configured PaperMC server jar."""

    install_downloaded_jar(server)
    cust.install(server, eula=eula)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env=requirements.get("env", {}),
        stdin_open=True,
        tty=True,
    )


def status(server, verbose):
    """Report PaperMC server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


command_functions["mod"] = paper_mod_command
