"""Wolfenstein: Enemy Territory dedicated server lifecycle helpers."""

import os
from pathlib import Path
import re
import shutil
import subprocess as sp
import tempfile

import downloader
import server.runtime as runtime_module
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.archive_install import ensure_executable, sync_tree
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

WET_DOWNLOAD_URL = "https://cdn.splashdamage.com/downloads/games/wet/et260b.x86_full.zip"
WET_DOWNLOAD_NAME = "et260b.x86_full.zip"
WET_INSTALLER_NAME = "et260b.x86_keygen_V03.run"
WET_MINIMAL_SERVER_CFG = """set dedicated \"2\"\nset sv_hostname \"AlphaGSM\"\nset net_port \"27960\"\nexec campaigncycle.cfg\n"""

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Wolfenstein: Enemy Territory in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "hostname")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    port_tokens=("+set", "net_port"),
    hostname_tokens=("+set", "sv_hostname"),
)
setting_schema = {
    "fs_game": _quake_launch_schema["fs_game"],
    "port": _quake_launch_schema["port"],
    "hostname": _quake_launch_schema["hostname"],
    "configfile": SettingSpec(
        canonical_key="configfile",
        description="Server config file to exec on startup.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+exec",),
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _fs_game(server) -> str:
    return str(server.data.get("fs_game") or "etmain")


def _configfile(server) -> str:
    return str(server.data.get("configfile") or "server.cfg")


def _config_path(server) -> str:
    return os.path.join(server.data["dir"], _fs_game(server), _configfile(server))


def _ensure_fs_game_backup(server):
    fs_game = _fs_game(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["etmain", "pb"]))
    for entry in ("etmain", "pb", fs_game):
        if entry not in backupfiles:
            backupfiles.append(entry)
    server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["etmain", "pb"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault(
        "default", {"targets": ["etmain", "pb"]}
    )
    targets = list(default_profile.setdefault("targets", ["etmain", "pb"]))
    for entry in ("etmain", "pb", fs_game):
        if entry not in targets:
            targets.append(entry)
    default_profile["targets"] = targets


def _write_managed_set_lines(config_path, *, hostname, port):
    updates = {
        "sv_hostname": hostname.replace('"', '\\"'),
        "net_port": str(int(port)),
    }
    seen = set()
    lines = []
    pattern = re.compile(r"^\s*(?://\s*)?set\s+(sv_hostname|net_port)\s+.*$")

    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as handle:
            for line in handle:
                match = pattern.match(line)
                if match is None:
                    lines.append(line)
                    continue
                key = match.group(1)
                lines.append(f'set {key} "{updates[key]}"\n')
                seen.add(key)

    for key in ("sv_hostname", "net_port"):
        if key not in seen:
            lines.append(f'set {key} "{updates[key]}"\n')

    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write("".join(lines))


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="bin/Linux/x86/etded.x86",
):
    """Collect and store configuration values for a Wolf: ET server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "fs_game": "etmain",
            "configfile": "server.cfg",
            "backupfiles": ["etmain", "pb"],
        },
    )
    gamemodule_common.ensure_backup_config(server, targets=["etmain", "pb"])
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27960,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Wolf: ET server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=WET_DOWNLOAD_URL,
        default_name=WET_DOWNLOAD_NAME,
        prompt="Direct archive URL for the Wolf: ET server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    _ensure_fs_game_backup(server)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download the official Linux installer and extract the dedicated payload."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(exe_path)
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], "zip")
        )
        installer_path = Path(downloadpath) / WET_INSTALLER_NAME
        if not installer_path.is_file():
            installer_candidates = sorted(Path(downloadpath).glob("*.run"))
            if not installer_candidates:
                raise ServerError("Wolf: ET installer payload not found in downloaded archive")
            installer_path = installer_candidates[0]
        with tempfile.TemporaryDirectory(prefix="alphagsm-wet-") as extract_dir:
            sp.run(
                ["sh", str(installer_path), "--noexec", "--target", extract_dir],
                check=True,
                stdout=sp.DEVNULL,
                stderr=sp.STDOUT,
            )
            sync_tree(extract_dir, server.data["dir"])
        server.data["current_url"] = server.data["url"]
    else:
        print("Skipping download")
    ensure_executable(exe_path)
    server.data.save()
    sync_server_config(server)


def sync_server_config(server):
    """Rewrite managed Wolf: ET config values inside the active server.cfg."""

    _ensure_fs_game_backup(server)
    config_path = _config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    if not os.path.isfile(config_path):
        default_config_path = os.path.join(server.data["dir"], "etmain", "server.cfg")
        if os.path.isfile(default_config_path) and os.path.normpath(default_config_path) != os.path.normpath(
            config_path
        ):
            shutil.copy2(default_config_path, config_path)
        else:
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write(WET_MINIMAL_SERVER_CFG)
    _write_managed_set_lines(
        config_path,
        hostname=server.data.get("hostname", "AlphaGSM %s" % (server.name,)),
        port=server.data.get("port", 27960),
    )


def get_start_command(server):
    """Build the command used to launch a Wolf: ET dedicated server."""

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
        [
            "./" + server.data["exe_name"],
            "+set",
            "net_strict",
            "1",
            "+set",
            "fs_homepath",
            "." if server.data.get("runtime") == "docker" else server.data["dir"],
            *launch_args,
        ],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for the Wolf: ET server."""

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
    """Return the Docker launch spec for Wolf: ET."""

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
    """Return the Quake UDP query address used by the wetserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the wetserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Wolf: ET using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Wolf: ET status is not implemented yet."""


def message(server, msg):
    """Wolf: ET has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Wolf: ET server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Wolf: ET datastore edits."""

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
        ),
        backup_module=backup_utils,
    )
