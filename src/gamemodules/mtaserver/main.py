"""Multi Theft Auto dedicated server lifecycle helpers."""

import html
import http.cookiejar
import os
from pathlib import Path
import re
import shutil
import tempfile
import urllib.request
from urllib.parse import urljoin

import screen
from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.providers import resolve_direct_url_entry, resolve_mta_community_entry
from server.modsupport.reconcile import reconcile_mod_state
from server.modsupport.registry import CuratedRegistryLoader
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MTA_DOWNLOADS_PAGE = "https://linux.multitheftauto.com/"
MTA_LATEST_DOWNLOAD_NAME = "multitheftauto_linux_x64.tar.gz"
MTA_MOD_CACHE_DIRNAME = "mtaserver"
MTA_ALLOWED_RESOURCE_SUFFIXES = {
    ".7z": "7z",
    ".tar.gz": "tar",
    ".tgz": "tar",
    ".tar.bz2": "tar",
    ".tbz2": "tar",
    ".tar.xz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".zip": "zip",
}
MTA_RESOURCE_DESTINATION = Path("mods") / "deathmatch" / "resources"
MTA_ALLOWED_RESOURCE_DESTINATIONS = (str(MTA_RESOURCE_DESTINATION),)

commands = ("mod",)
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Multi Theft Auto in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "manifest/curated, url, or community", str),
                ArgSpec(
                    "IDENTIFIER",
                    "resource family, resource archive URL, or MTA community resource page URL",
                    str,
                ),
                ArgSpec("EXTRA", "optional manifest channel or archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage Multi Theft Auto resources from the AlphaGSM manifest, direct archive URLs, or MTA community detail pages."
}
command_functions = {}
max_stop_wait = 1


def resolve_download(version=None):
    """Resolve a Multi Theft Auto x86_64 Linux server package."""

    req = urllib.request.Request(MTA_DOWNLOADS_PAGE, headers={"User-Agent": "AlphaGSM"})
    with urllib.request.urlopen(req) as response:
        page = response.read().decode("utf-8")
    ver_match = re.search(r"Version\s+([0-9]+(?:\.[0-9]+)+)", page)
    if not ver_match:
        raise ServerError("Unable to locate Multi Theft Auto Linux server downloads")
    resolved_version = ver_match.group(1)
    url_match = re.search(r'href="([^"]*multitheftauto_linux_x64\.tar\.gz)"', page)
    if not url_match:
        raise ServerError("Unable to locate Multi Theft Auto Linux server downloads")
    resolved_url = url_match.group(1)
    if not resolved_url.startswith("http"):
        resolved_url = MTA_DOWNLOADS_PAGE.rstrip("/") + "/" + resolved_url.lstrip("/")
    if version not in (None, "", "latest") and version != resolved_version:
        raise ServerError("Unable to locate the requested Multi Theft Auto version")
    return resolved_version, resolved_url


def load_mta_curated_registry(server=None):
    """Load the checked-in MTA resource registry or an override file."""

    del server
    override = os.environ.get("ALPHAGSM_MTASERVER_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


def _normalize_resource_name(raw_value: str) -> str:
    normalized = str(raw_value).replace(".", "_").strip()
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized)
    normalized = normalized.strip("_")
    if not normalized:
        raise ModSupportError("MTA resource name could not be derived from the upstream archive name")
    return normalized


def _resource_name_from_filename(filename: str) -> str:
    return _normalize_resource_name(Path(filename).stem)


def ensure_mod_state(server):
    """Seed the MTA resource desired-state shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("curated", [])
    desired.setdefault("url", [])
    desired.setdefault("community", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
    mods.setdefault("errors", [])
    return mods


def _save_data(server):
    save = getattr(server.data, "save", None)
    if callable(save):
        save()


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / MTA_MOD_CACHE_DIRNAME


def _resource_root(server) -> Path:
    return Path(server.data["dir"]) / MTA_RESOURCE_DESTINATION


def _desired_entries(server) -> list[DesiredModEntry]:
    entries = [
        DesiredModEntry(
            source_type="curated",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
            channel=entry.get("channel"),
        )
        for entry in ensure_mod_state(server)["desired"]["curated"]
    ]
    entries.extend(
        DesiredModEntry(
            source_type="url",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in ensure_mod_state(server)["desired"]["url"]
    )
    entries.extend(
        DesiredModEntry(
            source_type="community",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in ensure_mod_state(server)["desired"]["community"]
    )
    return entries


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


def _extract_archive(archive_path: Path, stage_root: Path, archive_type: str) -> None:
    if archive_type == "zip":
        extract_zip_safe(archive_path, stage_root)
        return
    if archive_type == "7z":
        extract_7z_safe(archive_path, stage_root)
        return
    extract_tarball_safe(archive_path, stage_root)


def _resource_dirs(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_dir() and (path / "meta.xml").is_file()
    ]


def _build_install_stage(stage_root: Path, *, default_resource_name: str | None = None) -> Path | None:
    candidates = [stage_root]
    if stage_root.exists():
        top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
        if len(top_level_dirs) == 1:
            candidates.append(top_level_dirs[0])

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        prefixed_root = candidate / MTA_RESOURCE_DESTINATION
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        if prefixed_root.is_dir():
            for source_path in sorted(path for path in prefixed_root.rglob("*") if path.is_file()):
                relative_path = source_path.relative_to(prefixed_root)
                destination = install_root / MTA_RESOURCE_DESTINATION / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                installed_any = True
        elif (candidate / "meta.xml").is_file():
            if not default_resource_name:
                raise ModSupportError("MTA resource archive root contains meta.xml but no resource name could be derived")
            for source_path in sorted(path for path in candidate.rglob("*") if path.is_file()):
                relative_path = source_path.relative_to(candidate)
                destination = install_root / MTA_RESOURCE_DESTINATION / default_resource_name / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                installed_any = True
        else:
            for resource_dir in _resource_dirs(candidate):
                for source_path in sorted(path for path in resource_dir.rglob("*") if path.is_file()):
                    relative_path = source_path.relative_to(resource_dir)
                    destination = install_root / MTA_RESOURCE_DESTINATION / resource_dir.name / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, destination)
                    installed_any = True

        if installed_any:
            return install_root
    return None


def _desired_record(server, source_type: str, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"][source_type]:
        if entry.get("resolved_id") == resolved_id:
            return entry
    raise ModSupportError(f"Missing MTA desired-state metadata for '{resolved_id}'")


def _install_archive_entry(
    server,
    desired_entry: DesiredModEntry,
    *,
    cache_subdir: str,
    filename: str,
    archive_type: str,
    resource_name: str,
    downloader,
) -> InstalledModEntry:
    cache_root = _cache_root(server) / cache_subdir
    cache_root.mkdir(parents=True, exist_ok=True)
    archive_path = cache_root / filename
    downloader(archive_path)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    _extract_archive(archive_path, stage_root, archive_type)

    install_root = _build_install_stage(stage_root, default_resource_name=resource_name)
    if install_root is None:
        raise ModSupportError(
            "No Multi Theft Auto resource content was found in the downloaded payload; expected mods/deathmatch/resources/<name>/... or a top-level resource directory containing meta.xml"
        )

    installed_paths = install_staged_tree(
        staged_root=install_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=MTA_ALLOWED_RESOURCE_DESTINATIONS,
    )
    return InstalledModEntry(
        source_type=desired_entry.source_type,
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _install_url_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    desired_record = _desired_record(server, "url", desired_entry.resolved_id)
    return _install_archive_entry(
        server,
        desired_entry,
        cache_subdir="url",
        filename=desired_record["filename"],
        archive_type=desired_record["archive_type"],
        resource_name=desired_record["resource_name"],
        downloader=lambda archive_path: download_to_cache(
            desired_record["download_url"],
            allowed_hosts=(desired_record["allowed_host"],),
            target_path=archive_path,
        ),
    )


def _install_curated_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    resolved = load_mta_curated_registry().resolve(desired_entry.requested_id, desired_entry.channel)
    if tuple(resolved.destinations) != MTA_ALLOWED_RESOURCE_DESTINATIONS:
        raise ModSupportError(
            f"Unsupported MTA manifest destinations for '{resolved.resolved_id}'"
        )
    resource_name = _normalize_resource_name(resolved.family)
    filename = Path(resolved.url).name or f"{resolved.resolved_id}.{resolved.archive_type}"
    return _install_archive_entry(
        server,
        desired_entry,
        cache_subdir="curated",
        filename=filename,
        archive_type=resolved.archive_type,
        resource_name=resource_name,
        downloader=lambda archive_path: download_to_cache(
            resolved.url,
            allowed_hosts=resolved.hosts,
            target_path=archive_path,
            checksum=resolved.checksum,
        ),
    )


def download_mta_community_resource(download_page_url, asset_path, *, target_path):
    """Download an MTA community resource archive via its cookie-backed flow."""

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_handle = None
    temp_path = None
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def _looks_like_html_payload(payload: bytes) -> bool:
        sample = payload.lstrip()[:128].lower()
        return sample.startswith((b"<!doctype html", b"<html", b"<head", b"<body"))

    try:
        request = urllib.request.Request(download_page_url, headers={"User-Agent": "AlphaGSM"})
        with opener.open(request, timeout=30) as response:
            response.read()

        asset_url = urljoin(download_page_url, asset_path)
        asset_request = urllib.request.Request(
            asset_url,
            headers={"User-Agent": "AlphaGSM", "Referer": download_page_url},
        )
        temp_handle, temp_name = tempfile.mkstemp(
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            dir=target_path.parent,
        )
        temp_path = Path(temp_name)
        with opener.open(asset_request, timeout=30) as response, open(temp_handle, "wb", closefd=True) as handle:
            content_type = str(response.headers.get("content-type") or "")
            first_chunk = response.read(64 * 1024)
            if content_type.startswith("text/html") or _looks_like_html_payload(first_chunk):
                preview = first_chunk[:512].decode("utf-8", errors="replace")
                raise ModSupportError(
                    "Failed to download MTA community archive: upstream returned HTML instead of a resource archive"
                    + ("" if not preview.strip() else f" ({html.unescape(preview.strip())[:120]})")
                )
            if first_chunk:
                handle.write(first_chunk)
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ModSupportError(f"Failed to download MTA community archive: {exc}") from exc

    if temp_path is not None:
        temp_path.replace(target_path)
    return target_path


def _install_community_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    desired_record = _desired_record(server, "community", desired_entry.resolved_id)
    return _install_archive_entry(
        server,
        desired_entry,
        cache_subdir="community",
        filename=desired_record["filename"],
        archive_type=desired_record["archive_type"],
        resource_name=desired_record["resource_name"],
        downloader=lambda archive_path: download_mta_community_resource(
            desired_record["download_page_url"],
            desired_record["asset_path"],
            target_path=archive_path,
        ),
    )


def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    if desired_entry.source_type == "curated":
        return _install_curated_entry(server, desired_entry)
    if desired_entry.source_type == "url":
        return _install_url_entry(server, desired_entry)
    if desired_entry.source_type == "community":
        return _install_community_entry(server, desired_entry)
    raise ModSupportError(f"Unsupported MTA mod source: {desired_entry.source_type}")


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"])
    resource_root = _resource_root(server).resolve()
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current.exists() and current != resource_root.parent:
            try:
                current.relative_to(resource_root)
            except ValueError:
                break
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def cleanup_configured_mods(server):
    mods = ensure_mod_state(server)
    for installed_entry in _installed_entries(server):
        _remove_owned_entry(server, installed_entry)
    shutil.rmtree(_cache_root(server), ignore_errors=True)
    mods["desired"] = {"curated": [], "url": [], "community": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    _save_data(server)


def apply_configured_mods(server):
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
        _save_data(server)
        if isinstance(exc, ServerError):
            raise
        raise ServerError(str(exc)) from exc
    mods["installed"] = _serialize_installed_entries(reconciled)
    mods["last_apply"] = "success"
    mods["errors"] = []
    _save_data(server)


def mta_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the MTA `mod` command desired-state subcommands."""

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
    if action == "add" and source in ("manifest", "curated"):
        if not identifier:
            raise ServerError("Multi Theft Auto mod add manifest requires a resource family")
        try:
            resolved = load_mta_curated_registry().resolve(identifier, extra)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        for entry in mods["desired"]["curated"]:
            if entry.get("resolved_id") == resolved.resolved_id:
                raise ServerError(
                    f"Multi Theft Auto manifest entry '{resolved.resolved_id}' is already present in desired state"
                )
        mods["desired"]["curated"].append(
            {
                "requested_id": identifier,
                "resolved_id": resolved.resolved_id,
                "channel": resolved.channel,
                "resource_name": _normalize_resource_name(resolved.family),
            }
        )
        _save_data(server)
        return
    if action == "add" and source == "url":
        if not identifier:
            raise ServerError("Multi Theft Auto mod add url requires a resource archive URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=MTA_ALLOWED_RESOURCE_SUFFIXES,
            entry_label="Multi Theft Auto resource URL entries",
            filename_description="a supported archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Multi Theft Auto resource '{resolved['requested_id']}' is already present in desired state"
                )
        resolved["resource_name"] = _resource_name_from_filename(resolved["filename"])
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "add" and source == "community":
        if not identifier:
            raise ServerError(
                "Multi Theft Auto mod add community requires a canonical MTA community resource page URL"
            )
        try:
            resolved = resolve_mta_community_entry(identifier)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        for entry in mods["desired"]["community"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Multi Theft Auto community entry '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["community"].append(resolved)
        _save_data(server)
        return
    raise ServerError("Unsupported Multi Theft Auto mod command")


command_functions["mod"] = mta_mod_command


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="mta-server64"
):
    """Collect and store configuration values for a Multi Theft Auto server."""

    server.data.setdefault("backupfiles", ["mods", "server", "mods/deathmatch/mtaserver.conf"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["mods", "server"]}},
            "schedule": [("default", 0, "days")],
        }
    if port is None:
        port = server.data.get("port", 22003)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Multi Theft Auto server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Multi Theft Auto server: [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = (
            os.path.basename(server.data.get("url", "")) or MTA_LATEST_DOWNLOAD_NAME
        )
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    ensure_mod_state(server)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Multi Theft Auto server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url) or MTA_LATEST_DOWNLOAD_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def get_start_command(server):
    """Build the command used to launch a Multi Theft Auto dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "--port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop MTA using the standard shutdown command."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed Multi Theft Auto status is not implemented yet."""


def message(server, msg):
    """Multi Theft Auto has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Multi Theft Auto server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Multi Theft Auto datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "version"),
    )

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
