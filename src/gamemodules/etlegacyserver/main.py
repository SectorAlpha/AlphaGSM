"""ET: Legacy dedicated server lifecycle helpers."""

import os
from pathlib import Path
import re
import shutil
import urllib.request

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
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

ETLEGACY_DOWNLOAD_PAGE = "https://www.etlegacy.com/download"
ETLEGACY_RELEASE_LIST_PAGE = "https://www.etlegacy.com/download/release/list"
ETLEGACY_MOD_CACHE_DIRNAME = "etlegacyserver"
ETLEGACY_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".pk3": "pk3",
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
    "The directory to install ET: Legacy in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "pk3 archive URL or direct pk3 URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage ET: Legacy pk3 content from direct archive URLs or direct pk3 URLs into the active fs_game directory."
}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "hostname")
_quake_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    port_tokens=("+set", "net_port"),
    hostname_tokens=("+set", "sv_hostname"),
)
setting_schema = {
    "fs_game": _quake_schema["fs_game"],
    "port": SettingSpec(
        canonical_key="port",
        description=_quake_schema["port"].description,
        value_type=_quake_schema["port"].value_type,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="net_port",
        launch_arg_tokens=_quake_schema["port"].launch_arg_tokens,
    ),
    "hostname": SettingSpec(
        canonical_key="hostname",
        description=_quake_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="sv_hostname",
        launch_arg_tokens=_quake_schema["hostname"].launch_arg_tokens,
    ),
    "configfile": SettingSpec(
        canonical_key="configfile",
        description="Server config file to exec on startup.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+exec",),
    ),
    **gamemodule_common.build_versioned_download_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the ET: Legacy mod desired-state shape and return it."""

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


def _fs_game(server) -> str:
    return str(server.data.get("fs_game") or "legacy")


def _ensure_fs_game_backup(server):
    fs_game = _fs_game(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["legacy", "etmain"]))
    if fs_game not in backupfiles:
        backupfiles.append(fs_game)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["legacy", "etmain"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault(
        "default", {"targets": ["legacy", "etmain"]}
    )
    targets = list(default_profile.setdefault("targets", ["legacy", "etmain"]))
    if fs_game not in targets:
        targets.append(fs_game)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / ETLEGACY_MOD_CACHE_DIRNAME


def _allowed_destinations(server) -> tuple[str, ...]:
    return (_fs_game(server),)


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


def _pk3_files(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_file() and path.name.lower().endswith(".pk3")
    ]


def _build_install_stage(stage_root: Path, *, fs_game: str) -> Path | None:
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

        prefixed_root = candidate / fs_game
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        source_roots = []
        if prefixed_root.is_dir():
            source_roots.append(prefixed_root)
        pk3_sources = _pk3_files(candidate)
        if pk3_sources:
            source_roots.append(candidate)

        for source_root in source_roots:
            for source_path in _pk3_files(source_root):
                destination = install_root / fs_game / source_path.name
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
    raise ModSupportError(f"Missing ET: Legacy desired-state metadata for '{resolved_id}'")


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

    fs_game = _fs_game(server)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root, fs_game=fs_game)
        if install_root is None:
            raise ModSupportError(
                f"No ET: Legacy pk3 content was found in the downloaded payload; expected {fs_game}/<name>.pk3 or bare .pk3 files"
            )
    else:
        stage_single_file(archive_path, stage_root, Path(fs_game) / desired_record["filename"])
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
    _ensure_fs_game_backup(server)
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


def etlegacy_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the ET: Legacy `mod` command desired-state subcommands."""

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
            raise ServerError("ET: Legacy mod add url requires a pk3 archive URL or direct pk3 URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=ETLEGACY_ALLOWED_MOD_SUFFIXES,
            entry_label="ET: Legacy mod URL entries",
            filename_description="a supported pk3 or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"ET: Legacy content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("ET: Legacy mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"ET: Legacy content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported ET: Legacy mod command")


command_functions["mod"] = etlegacy_mod_command


def _read_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "AlphaGSM/1.0"})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8", "replace")


def _parse_release_page(page_html):
    version_match = re.search(r"stable release ([0-9.]+)", page_html, re.IGNORECASE)
    download_match = re.search(
        r"Linux.*?data-href=\"(https://www\.etlegacy\.com/download/file/\d+)\">x86_64 archive",
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if version_match is None or download_match is None:
        raise ServerError("Unable to locate a suitable ET: Legacy Linux download")
    version = version_match.group(1)
    return version, download_match.group(1)


def resolve_download(version=None):
    """Resolve an ET: Legacy Linux server archive from the official downloads site."""

    if version in (None, "", "latest"):
        return _parse_release_page(_read_page(ETLEGACY_DOWNLOAD_PAGE))

    release_list = _read_page(ETLEGACY_RELEASE_LIST_PAGE)
    release_match = re.search(
        r'href="https://www\.etlegacy\.com/download/release/(\d+)">%s\b'
        % re.escape(str(version)),
        release_list,
        re.IGNORECASE,
    )
    if release_match is None:
        raise ServerError("Unable to locate the requested ET: Legacy release")
    release_url = "https://www.etlegacy.com/download/release/%s" % (release_match.group(1),)
    resolved_version, resolved_url = _parse_release_page(_read_page(release_url))
    return resolved_version, resolved_url


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="etl.x86_64",
):
    """Collect and store configuration values for an ET: Legacy server."""

    server.data.setdefault("fs_game", "legacy")
    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("configfile", "etl_server.cfg")
    server.data.setdefault("backupfiles", ["legacy", "etmain"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["legacy", "etmain"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27960)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the ET: Legacy server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        requested_version = version or server.data.get("version")
        resolved_version, resolved_url = resolve_download(version=requested_version)
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input(
            "Direct archive URL for the ET: Legacy server: [%s] " % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        if server.data.get("version"):
            server.data["download_name"] = "etlegacy-v%s-x86_64.tar.gz" % (server.data["version"],)
        else:
            server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "etlegacy.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    ensure_mod_state(server)
    _ensure_fs_game_backup(server)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the ET: Legacy server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", "etlegacy-v%s-x86_64.tar.gz" % (resolved_version,))
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def sync_server_config(server):
    """Rewrite managed etl_server.cfg entries from datastore values."""

    _ensure_fs_game_backup(server)
    config_path = os.path.join(
        server.data["dir"],
        server.data.get("configfile", "etl_server.cfg"),
    )
    if not os.path.isfile(config_path):
        return
    replacements = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 27960,
            "hostname": "AlphaGSM %s" % (server.name,),
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            str(int(current_value))
            if spec.value_type == "integer"
            else '"%s"' % (str(current_value),)
        ),
    )
    if not replacements:
        return
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
    new_content = content
    for native_key, native_value in replacements.items():
        new_content = re.sub(
            rf'(^\s*set\s+{re.escape(native_key)}\s+)(.*?)(\s*$)',
            r'\g<1>' + native_value + r'\g<3>',
            new_content,
            flags=re.MULTILINE,
        )
    if new_content != content:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)


def get_start_command(server):
    """Build the command used to launch an ET: Legacy dedicated server."""

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
        ["./" + server.data["exe_name"], *launch_args, "+set", "dedicated", "2"],
        server.data["dir"],
    )


def get_query_address(server):
    """ET: Legacy uses the Quake3/ioquake3 getstatus query on the game port."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake3 address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


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
    """Return the Docker launch spec for ET: Legacy."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def do_stop(server, j):
    """Stop ET: Legacy using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed ET: Legacy status is not implemented yet."""


def message(server, msg):
    """ET: Legacy has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ET: Legacy server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ET: Legacy datastore edits."""

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
            "fs_game",
            "configfile",
            "hostname",
            "version",
        ),
        backup_module=backup_utils,
    )
