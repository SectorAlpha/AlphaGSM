"""Unreal Tournament 99 dedicated server lifecycle helpers."""

import os
from pathlib import Path
import shutil
import stat
import subprocess as sp

import downloader
import screen
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
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

UT99_INSTALLER_URL = (
    "https://raw.githubusercontent.com/OldUnreal/FullGameInstallers/master/Linux/install-ut99.sh"
)
UT99_INSTALLER_NAME = "install-ut99.sh"
UT99_LAYOUT_CANDIDATES = (
    ("System64/ucc-bin-amd64", "System64/UnrealTournament.ini"),
    ("System64/ucc-bin", "System64/UnrealTournament.ini"),
    ("SystemARM64/ucc-bin-arm64", "SystemARM64/UnrealTournament.ini"),
    ("SystemARM64/ucc-bin", "SystemARM64/UnrealTournament.ini"),
    ("System64/ut-bin-amd64", "System64/UnrealTournament.ini"),
    ("SystemARM64/ut-bin-arm64", "SystemARM64/UnrealTournament.ini"),
    ("System/ucc-bin", "System/UnrealTournament.ini"),
)
UT99_MOD_CACHE_DIRNAME = "ut99server"
UT99_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".tar.gz": "tar",
    ".tbz2": "tar",
    ".tgz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".tar.bz2": "tar",
    ".tar.xz": "tar",
    ".uax": "uax",
    ".umx": "umx",
    ".unr": "unr",
    ".utx": "utx",
    ".zip": "zip",
}
UT99_ALLOWED_DESTINATIONS = ("Maps", "Music", "Sounds", "Textures")
UT99_DESTINATION_BY_LOWER = {value.lower(): value for value in UT99_ALLOWED_DESTINATIONS}
UT99_SINGLE_FILE_DESTINATIONS = {
    ".uax": "Sounds",
    ".umx": "Music",
    ".unr": "Maps",
    ".utx": "Textures",
}
UT99_IGNORED_TOP_LEVEL_SUFFIXES = {
    ".bmp",
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".md",
    ".nfo",
    ".pdf",
    ".png",
    ".rtf",
    ".txt",
}


def _require_ut99_installer_prerequisites():
    """Raise when the OldUnreal installer prerequisites are not present."""

    if shutil.which("7zz") or shutil.which("7z"):
        return
    raise ServerError(
        "UT99 installer requires a 7z-compatible extractor. "
        "Install p7zip-full or another package that provides 7z/7zz."
    )


def _sync_installed_layout(server):
    """Update stored executable/config paths to match the installed UT99 layout."""

    dir_path = server.data["dir"]
    configfile = server.data.get("configfile")
    managed_config_paths = {ini_path for _exe_path, ini_path in UT99_LAYOUT_CANDIDATES}

    for exe_name, config_path in UT99_LAYOUT_CANDIDATES:
        if not os.path.isfile(os.path.join(dir_path, exe_name)):
            continue
        server.data["exe_name"] = exe_name
        if not configfile or configfile in managed_config_paths:
            server.data["configfile"] = config_path
        return

commands = ("mod",)
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Unreal Tournament 99 in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "content archive URL or direct content file URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage Unreal Tournament 99 custom content from direct archive URLs or direct content-file URLs."
}
command_functions = {}
max_stop_wait = 1


def ensure_mod_state(server):
    """Seed the UT99 content desired-state shape and return it."""

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


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / UT99_MOD_CACHE_DIRNAME


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


def _content_destination_for_name(filename: str) -> str | None:
    lower_name = str(filename).lower()
    for suffix, destination in UT99_SINGLE_FILE_DESTINATIONS.items():
        if lower_name.endswith(suffix):
            return destination
    return None


def _should_ignore_archive_path(relative_path: Path) -> bool:
    parts = [part.lower() for part in relative_path.parts]
    if any(part == "__macosx" for part in parts):
        return True
    if len(relative_path.parts) != 1:
        return False
    basename = relative_path.name.lower()
    if basename in ("thumbs.db", ".ds_store"):
        return True
    return Path(basename).suffix in UT99_IGNORED_TOP_LEVEL_SUFFIXES


def _build_install_stage(stage_root: Path) -> Path | None:
    candidates = [stage_root]
    if stage_root.exists():
        top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
        if len(top_level_dirs) == 1:
            candidates.append(top_level_dirs[0])

    seen = set()
    for candidate in candidates:
        resolved_candidate = candidate.resolve()
        if resolved_candidate in seen:
            continue
        seen.add(resolved_candidate)

        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        for source_path in sorted(path for path in candidate.rglob("*") if path.is_file()):
            relative_path = source_path.relative_to(candidate)
            destination_relative = None
            if relative_path.parts and relative_path.parts[0].lower() in UT99_DESTINATION_BY_LOWER:
                destination_relative = Path(
                    UT99_DESTINATION_BY_LOWER[relative_path.parts[0].lower()]
                ).joinpath(*relative_path.parts[1:])
            elif len(relative_path.parts) == 1:
                destination = _content_destination_for_name(source_path.name)
                if destination is not None:
                    destination_relative = Path(destination) / source_path.name
                elif _should_ignore_archive_path(relative_path):
                    continue
                else:
                    raise ModSupportError(
                        f"Unsupported UT99 archive payload: {relative_path.as_posix()}"
                    )
            elif _should_ignore_archive_path(relative_path):
                continue
            else:
                raise ModSupportError(
                    "UT99 content archives must unpack into Maps/, Music/, Sounds/, or Textures/"
                )

            destination_path = install_root / destination_relative
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)
            installed_any = True

        if installed_any:
            return install_root
    return None


def _desired_record(server, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"]["url"]:
        if entry.get("resolved_id") == resolved_id:
            return entry
    raise ModSupportError(f"Missing UT99 desired-state metadata for '{resolved_id}'")


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

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root)
        if install_root is None:
            raise ModSupportError(
                "No UT99 content files were found in the downloaded payload; expected approved content directories or bare map/content files"
            )
    else:
        destination = _content_destination_for_name(desired_record["filename"])
        if destination is None:
            raise ModSupportError(
                f"Unsupported direct UT99 content file: {desired_record['filename']}"
            )
        stage_single_file(archive_path, stage_root, Path(destination) / desired_record["filename"])
        install_root = stage_root

    installed_paths = install_staged_tree(
        staged_root=install_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=UT99_ALLOWED_DESTINATIONS,
    )
    return InstalledModEntry(
        source_type=desired_entry.source_type,
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"]).resolve()
    approved_roots = [server_root / destination for destination in UT99_ALLOWED_DESTINATIONS]
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current.exists() and current != server_root:
            if not any(_path_is_within(current, approved_root) for approved_root in approved_roots):
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
    mods["desired"] = {"url": []}
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


def ut99_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the UT99 `mod` command desired-state subcommands."""

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
            raise ServerError(
                "Unreal Tournament 99 mod add url requires a content archive URL or direct content file URL"
            )
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=UT99_ALLOWED_MOD_SUFFIXES,
            entry_label="Unreal Tournament 99 mod URL entries",
            filename_description="a supported UT99 content filename or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Unreal Tournament 99 content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("Unreal Tournament 99 mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(
                f"Unreal Tournament 99 content '{identifier}' is not present in desired state"
            )
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported Unreal Tournament 99 mod command")


command_functions["mod"] = ut99_mod_command


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="System/ucc-bin",
):
    """Collect and store configuration values for an Unreal Tournament 99 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "DM-Deck16][",
            "gametype": "Botpack.DeathMatchPlus",
            "maxplayers": "16",
            "configfile": "System/UnrealTournament.ini",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["System", "Maps"],
        targets=["System", "Maps"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Unreal Tournament 99 server:",
    )
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = UT99_INSTALLER_URL
        server.data["download_mode"] = "installer"
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Unreal Tournament 99 server override [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    gamemodule_common.configure_download_source(
        server,
        ask=False,
        url=server.data.get("url"),
        download_name=download_name,
        default_name=UT99_INSTALLER_NAME,
        prompt="",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Install Unreal Tournament 99 using the OldUnreal Linux installer."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = UT99_INSTALLER_URL
        server.data.setdefault("download_name", UT99_INSTALLER_NAME)
        server.data["download_mode"] = "installer"
    if server.data.get("download_mode") == "installer":
        _require_ut99_installer_prerequisites()
        download_path = downloader.getpath("url", (server.data["url"], server.data["download_name"]))
        installer_path = os.path.join(download_path, server.data["download_name"])
        mode = os.stat(installer_path).st_mode
        os.chmod(installer_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        _sync_installed_layout(server)
        if (
            server.data.get("current_url") != server.data["url"]
            or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
        ):
            sp.run(
                [
                    installer_path,
                    "--destination",
                    server.data["dir"],
                    "--ui-mode",
                    "none",
                    "--application-entry",
                    "skip",
                    "--desktop-shortcut",
                    "skip",
                ],
                input="y\n",
                text=True,
                check=True,
            )
            _sync_installed_layout(server)
            server.data["current_url"] = server.data["url"]
            server.data.save()
        else:
            print("Skipping download")
        ensure_mod_state(server)
        if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
            apply_configured_mods(server)
        return
    install_archive(server, detect_compression(server.data["download_name"]))
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def get_start_command(server):
    """Build the command used to launch an Unreal Tournament 99 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return _runtime_command(server)


def _runtime_command(server):
    """Return the UT99 runtime command without install-time existence checks."""

    return (
        [
            "./" + server.data["exe_name"],
            "server",
            "%s?Game=%s?MaxPlayers=%s" % (
                server.data["startmap"],
                server.data["gametype"],
                server.data["maxplayers"],
            ),
            "-port=%s" % (server.data["port"],),
            "-ini=%s" % (server.data["configfile"],),
            "-log=server.log",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Unreal Tournament 99 using the standard console command."""

    screen.send_to_server(server.name, "\nexit\n")


def get_query_address(server):
    """Probe the UT99 game socket as generic UDP reachability."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Use UDP reachability for UT99 info until a richer protocol is implemented."""

    return get_query_address(server)


def status(server, verbose):
    """Detailed Unreal Tournament 99 status is not implemented yet."""


def message(server, msg):
    """Unreal Tournament 99 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Unreal Tournament 99 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Unreal Tournament 99 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "startmap",
            "gametype",
            "maxplayers",
            "configfile",
            "download_mode",
        ),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

def get_container_spec(server):
    command, _cwd = _runtime_command(server)
    requirements = runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )
    return {
        "working_dir": runtime_module.DEFAULT_CONTAINER_WORKDIR,
        "stdin_open": True,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": list(command),
    }
