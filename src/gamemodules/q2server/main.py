"""Quake 2 dedicated server lifecycle helpers."""

import os
from pathlib import Path
import re
import shutil
import subprocess as sp
import urllib.parse
import urllib.request

import downloader
import screen
import server.runtime as runtime_module
from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
    stage_single_file,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.providers import resolve_direct_url_entry
from server.modsupport.reconcile import reconcile_mod_state
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.archive_install import detect_compression, install_archive
from utils.archive_install import resolve_archive_root, sync_tree
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.github_releases import HTTP_USER_AGENT, read_json
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_equals_config

YAMAGI_Q2_PAGE = "https://www.yamagi.org/quake2/"
YAMAGI_Q2_TAGS_API = "https://api.github.com/repos/yquake2/yquake2/tags?per_page=100"
Q2_MOD_CACHE_DIRNAME = "q2server"
Q2_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".pak": "pak",
    ".tar.gz": "tar",
    ".tbz2": "tar",
    ".tgz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".tar.bz2": "tar",
    ".tar.xz": "tar",
    ".zip": "zip",
}

commands = ("mod",)
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Quake 2 in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "pak archive URL or direct pak URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage Quake 2 pak content from direct archive URLs or direct pak URLs into the active gamedir."
}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "gamedir", "startmap")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    game_key="gamedir",
    game_aliases=("game",),
    game_description="The active Quake 2 game directory.",
    fs_game_tokens=("+set", "game"),
    port_tokens=("+set", "port"),
    hostname_tokens=("+set", "hostname"),
    hostname_before_port=True,
)
setting_schema = {
    "fs_game": _quake_launch_schema["fs_game"],
    "hostname": SettingSpec(
        canonical_key="hostname",
        aliases=_quake_launch_schema["hostname"].aliases,
        description=_quake_launch_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="hostname",
        launch_arg_tokens=_quake_launch_schema["hostname"].launch_arg_tokens,
    ),
    "port": _quake_launch_schema["port"],
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=_quake_launch_schema["startmap"].aliases,
        description=_quake_launch_schema["startmap"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="startmap",
        launch_arg_tokens=_quake_launch_schema["startmap"].launch_arg_tokens,
    ),
    **gamemodule_common.build_versioned_download_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
    "download_mode": SettingSpec(canonical_key="download_mode", description="How the server should be installed."),
}


def ensure_mod_state(server):
    """Seed the Quake 2 mod desired-state shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("url", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
    mods.setdefault("errors", [])
    return mods


def _save_data(server):
    save = getattr(server.data, "save", None)
    if callable(save):
        save()


def _gamedir(server) -> str:
    return str(server.data.get("gamedir") or "baseq2")


def _ensure_gamedir_backup(server):
    gamedir = _gamedir(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["baseq2"]))
    if gamedir not in backupfiles:
        backupfiles.append(gamedir)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["baseq2"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault("default", {"targets": ["baseq2"]})
    targets = list(default_profile.setdefault("targets", ["baseq2"]))
    if gamedir not in targets:
        targets.append(gamedir)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / Q2_MOD_CACHE_DIRNAME


def _allowed_destinations(server) -> tuple[str, ...]:
    return (_gamedir(server),)


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


def _extract_archive(archive_path: Path, stage_root: Path, archive_type: str) -> None:
    if archive_type == "zip":
        extract_zip_safe(archive_path, stage_root)
        return
    if archive_type == "7z":
        extract_7z_safe(archive_path, stage_root)
        return
    extract_tarball_safe(archive_path, stage_root)


def _pak_files(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_file() and path.name.lower().endswith(".pak")
    ]


def _build_install_stage(stage_root: Path, *, gamedir: str) -> Path | None:
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

        prefixed_root = candidate / gamedir
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        source_roots = []
        if prefixed_root.is_dir():
            source_roots.append(prefixed_root)
        if _pak_files(candidate):
            source_roots.append(candidate)

        for source_root in source_roots:
            for source_path in _pak_files(source_root):
                destination = install_root / gamedir / source_path.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                installed_any = True

        if installed_any:
            return install_root
    return None


def _desired_record(server, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"]["url"]:
        if entry.get("resolved_id") == resolved_id:
            return entry
    raise ModSupportError(f"Missing Quake 2 desired-state metadata for '{resolved_id}'")


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

    gamedir = _gamedir(server)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root, gamedir=gamedir)
        if install_root is None:
            raise ModSupportError(
                f"No Quake 2 pak content was found in the downloaded payload; expected {gamedir}/<name>.pak or bare .pak files"
            )
    else:
        stage_single_file(archive_path, stage_root, Path(gamedir) / desired_record["filename"])
        install_root = stage_root

    installed_paths = install_staged_tree(
        staged_root=install_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=_allowed_destinations(server),
    )
    return InstalledModEntry(
        source_type=desired_entry.source_type,
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"]).resolve()
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current.exists() and current != server_root:
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
    mods["desired"] = {"url": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    _save_data(server)


def apply_configured_mods(server):
    mods = ensure_mod_state(server)
    if not mods.get("enabled", True):
        return
    _ensure_gamedir_backup(server)
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_url_entry(server, entry),
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


def q2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the Quake 2 `mod` command desired-state subcommands."""

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
            raise ServerError("Quake 2 mod add url requires a pak archive URL or direct pak URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=Q2_ALLOWED_MOD_SUFFIXES,
            entry_label="Quake 2 mod URL entries",
            filename_description="a supported pak or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Quake 2 content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("Quake 2 mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"Quake 2 content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported Quake 2 mod command")


command_functions["mod"] = q2_mod_command


def resolve_download(version=None):
    """Resolve the official Yamagi Quake II source archive."""

    if version not in (None, "", "latest"):
        tags = read_json(YAMAGI_Q2_TAGS_API)
        for tag in tags:
            tag_name = tag.get("name", "")
            if str(version) in tag_name:
                archive_url = (
                    "https://github.com/yquake2/yquake2/archive/refs/tags/%s.tar.gz"
                    % (urllib.parse.quote(tag_name, safe=""),)
                )
                return str(version), archive_url
        raise ServerError("Unable to locate the requested Yamagi Quake II version")
    request = urllib.request.Request(YAMAGI_Q2_PAGE, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        page = response.read().decode("utf-8")
    match = re.search(
        r'href="([^"]+)">Yamagi Quake II, Version ([0-9.]+)',
        page,
        re.IGNORECASE,
    )
    if match is None:
        raise ServerError("Unable to locate the latest Yamagi Quake II source archive")
    return match.group(2), urllib.parse.urljoin(YAMAGI_Q2_PAGE, match.group(1))


def _install_from_source(server):
    """Build q2ded from the resolved Yamagi Quake II source archive."""

    downloadpath = downloader.getpath(
        "url", (server.data["url"], server.data["download_name"], "tar.gz")
    )
    source_root = resolve_archive_root(downloadpath)
    if (
        server.data.get("current_url") != server.data["url"]
        or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
    ):
        sp.run(["make"], cwd=source_root, check=True)
        sync_tree(source_root, server.data["dir"])
        server.data["current_url"] = server.data["url"]
        server.data.save()
    else:
        print("Skipping download")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="q2ded",
):
    """Collect and store configuration values for a Quake 2 server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("gamedir", "baseq2")
    server.data.setdefault("startmap", "q2dm1")
    server.data.setdefault("backupfiles", ["baseq2"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["baseq2"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27910)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Quake 2 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
        server.data["download_mode"] = "archive"
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data["download_mode"] = "source-build"
    if ask and url is None:
        inp = input("Direct archive URL for the Quake 2 server override [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "q2server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    ensure_mod_state(server)
    _ensure_gamedir_backup(server)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Quake 2 server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
        server.data["download_mode"] = "source-build"
    if server.data.get("download_mode") == "source-build":
        _install_from_source(server)
        sync_server_config(server)
        ensure_mod_state(server)
        if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
            apply_configured_mods(server)
        return
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def sync_server_config(server):
    """Rewrite managed Quake 2 config entries from datastore values."""

    _ensure_gamedir_backup(server)
    gamedir = server.data.get("gamedir", "baseq2")
    config_dir = os.path.join(server.data["dir"], gamedir)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "server.cfg")
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "q2dm1",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            '"%s"' % (str(current_value),)
            if spec.canonical_key == "hostname"
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


def get_start_command(server):
    """Build the command used to launch a Quake 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for native Linux Quake-family servers."""

    requirements = {
        "engine": "docker",
        "family": "quake-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Quake 2."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the Quake UDP query address used by the q2server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the q2server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake 2 using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 2 status is not implemented yet."""


def message(server, msg):
    """Quake 2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Quake 2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "gamedir",
            "startmap",
            "hostname",
            "version",
            "download_mode",
        ),
        backup_module=backup_utils,
    )
