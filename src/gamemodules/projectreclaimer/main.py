"""Project Reclaimer dedicated server with operator-owned MCC assets."""

import hashlib
import json
import os
from pathlib import Path
import re
import secrets

from server import ServerError
import server.runtime as runtime_module
from server.modsupport.downloads import download_to_cache
from server.modsupport.errors import ModSupportError
from server.settable_keys import SettingSpec
from utils import proton, reclaimer
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.gamemodules import common as gamemodule_common
from utils.platform_info import IS_LINUX
from utils.state_io import atomic_write_text

module_contract_version = 1
process_platforms = ("windows", "linux")
process_architectures = ("x86_64",)
SERVER_VERSION = "0.9.18"
SERVER_SHA256 = "eba2e3b5d6f8de8c8bb9c1d0913bcf5bbbf9c3f4e7c43afe9873340d93e443e3"
SERVER_URL = ("https://github.com/ProjectReclaimer/project-reclaimer-releases/releases/download/"
              f"v{SERVER_VERSION}/project-reclaimer-dedicated-v{SERVER_VERSION}.exe")
PORT_DEFINITIONS = (("port", "udp"), ("rconport", "tcp"))
commands = ("update", "rcon")
command_args = gamemodule_common.build_setup_command_args("Game UDP port", "Server installation directory")
command_args["rcon"] = CmdSpec(requiredarguments=(ArgSpec("COMMAND", "One quoted RCON command line", str),))
command_args["update"] = CmdSpec()
command_descriptions = {"update": "Install the pinned supported Reclaimer release.", "rcon": "Run a Reclaimer RCON command."}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "rconport", "servername", "maxplayers", "map", "gamemode", "rconpassword")
setting_schema = {
    key: SettingSpec(canonical_key=key, value_type="integer" if key in ("port", "rconport", "maxplayers") else "string",
                     secret=key == "rconpassword", apply_to=("datastore", "native_config"),
                     description="Reclaimer " + key + ".")
    for key in config_sync_keys
}


def configure(server, ask, port=None, dir=None):
    """Configure one managed Reclaimer instance; setup can precede asset import."""
    gamemodule_common.configure_port(server, ask, port, default_port=49176, prompt="Game UDP port:")
    checkvalue(server, ["port"], str(server.data["port"]))
    gamemodule_common.configure_install_dir(server, ask, dir, prompt="Reclaimer installation directory:")
    server.data["dir"] = str(Path(server.data["dir"]).expanduser().absolute())
    server.data.setdefault("rconport", int(server.data["port"]) + 1 if int(server.data["port"]) < 65535 else 65534)
    server.data.setdefault("servername", ("AlphaGSM " + server.name)[:48])
    server.data.setdefault("maxplayers", 16)
    server.data.setdefault("map", "Guardian")
    server.data.setdefault("gamemode", "Slayer")
    server.data.setdefault("rconpassword", secrets.token_urlsafe(32))
    server.data.setdefault("exe_name", "project-reclaimer.exe")
    for key in ("rconport", "maxplayers", "servername", "rconpassword", "map"):
        checkvalue(server, [key], str(server.data[key]))
    gamemodule_common.ensure_backup_config(server, backupfiles=["dedicated.toml", "content", "playlists", "bans.json"],
                                         targets=["dedicated.toml", "content", "playlists", "bans.json"])
    return gamemodule_common.finalize_configure(server)


def get_asset_requirements(server):
    """Copy only Halo 3 static engine/map files from MCC or a prepared export."""
    map_name = str(server.data.get("map", "Guardian")).casefold()
    return {"roots": ("", "game"), "include": ("halo3/*.dll", "halo3/maps/*.map"),
            "required": ("halo3/halo3.dll", "halo3/maps/shared.map", "halo3/maps/campaign.map",
                         "halo3/maps/040_voi.map", f"halo3/maps/{map_name}.map"),
            "target": "game", "case_insensitive": True}


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def install(server):
    """Install only the public server program; owned game assets stay separate."""
    root = Path(server.data["dir"])
    root.mkdir(parents=True, exist_ok=True)
    for subdir in ("game", "content/Maps", "content/Game Modes", "content/Mods", "playlists"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
    executable = root / "project-reclaimer.exe"
    if not executable.is_file() or _sha256(executable) != SERVER_SHA256:
        try:
            download_to_cache(SERVER_URL, allowed_hosts=("github.com",), target_path=executable, checksum=SERVER_SHA256)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
    server.data["installed_version"] = SERVER_VERSION
    sync_server_config(server)
    server.data.save()


def _rewrite_section(text, header, values):
    """Rewrite managed TOML scalar keys while preserving other lines/comments."""
    sections = re.split(r"(?m)(?=^[ \t]*\[)", text)
    index = next((i for i, section in enumerate(sections)
                  if section.splitlines() and section.splitlines()[0].split("#", 1)[0].strip() == header), None)
    if not header:
        index = 0
    if index is None:
        sections.append(header + "\n" if header else "")
        index = len(sections) - 1
    section = sections[index]
    for key, value in values.items():
        replacement = key + " = " + json.dumps(value, ensure_ascii=False)
        pattern = r"(?m)^[ \t]*" + re.escape(key) + r"[ \t]*=[^\r\n]*"
        if re.search(pattern, section):
            section = re.sub(pattern, lambda _match, line=replacement: line, section)
        else:
            section = section.rstrip() + "\n" + replacement + "\n"
    sections[index] = section
    return "\n".join(section.strip("\n") for section in sections if section.strip()) + "\n"


def sync_server_config(server):
    """Persist managed values in dedicated.toml without copying source config."""
    root = Path(server.data["dir"])
    root.mkdir(parents=True, exist_ok=True)
    path = root / "dedicated.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if len(re.findall(r"(?m)^[ \t]*\[\[server\]\][ \t]*(?:#.*)?$", text)) > 1:
        raise ServerError("Use one [[server]] per AlphaGSM Project Reclaimer installation")
    server_section = next((part for part in re.split(r"(?m)(?=^[ \t]*\[)", text)
                           if part.lstrip().startswith("[[server]]")), "")
    if re.search(r"(?m)^[ \t]*(playlist|variant|campaign)[ \t]*=", server_section):
        raise ServerError("This module manages fixed map/game selection; existing playlist, variant or campaign selection is preserved but requires manual integration")
    # The first segment is the top-level TOML table, before any section header.
    text = _rewrite_section(text, "", {"game": "game", "content": "content", "auto_update": False})
    text = _rewrite_section(text, "[master]", {"enabled": False})
    text = _rewrite_section(text, "[rcon]", {"password": server.data["rconpassword"], "address": "127.0.0.1"})
    text = _rewrite_section(text, "[[server]]", {
        "name": server.data["servername"], "port": int(server.data["port"]),
        "rcon_port": int(server.data["rconport"]), "max_players": int(server.data["maxplayers"]),
        "rcon_password": server.data["rconpassword"],
        "map": server.data["map"], "game": server.data["gamemode"],
    })
    atomic_write_text(path, text, mode=0o600)


def prestart(server):
    """Fail before launching Wine when required owned game files are missing."""
    from utils.asset_import import check_assets
    report = check_assets(server.data["dir"], get_asset_requirements(server))
    if not report["ready"]:
        raise ServerError("Project Reclaimer assets missing: " + ", ".join(report["missing"])
                          + ". Use setup --assets PATH or assets import PATH from an owned MCC installation.")
    sync_server_config(server)


def get_start_command(server):
    """Launch natively on Windows or explicitly through Wine on Linux."""
    executable = Path(server.data["dir"]).absolute() / "project-reclaimer.exe"
    if not executable.is_file():
        raise ServerError("Reclaimer executable missing; run setup first")
    command = ["./project-reclaimer.exe" if server.data.get("runtime") == "docker" else str(executable), "dedicated"]
    if IS_LINUX:
        command = proton.wrap_command(command, wineprefix=str(executable.parent / ".alphagsm-wineprefix"))
    return command, str(executable.parent)


def get_query_address(server):
    # RCON binds loopback on the host network, independently of game advertising.
    return ("127.0.0.1", int(server.data.get("rconport", 49177)), "reclaimer_rcon")


def get_info_address(server):
    return get_query_address(server)


def rcon(server, command):
    host, port, _protocol = get_query_address(server)
    reply = reclaimer.command(host, port, server.data["rconpassword"], command)
    if reply.get("text"):
        print(reply["text"].replace(server.data["rconpassword"], "<redacted>"))
    return reply


def message(server, msg):
    rcon(server, "say " + msg)


def do_stop(server, _attempt):
    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    server.info()


def backup(server, profile=None):
    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    original_key = [key] if isinstance(key, str) else key
    if original_key and original_key[0] == "backup":
        return gamemodule_common.handle_basic_checkvalue(server, original_key, *value)
    if isinstance(key, (tuple, list)):
        if len(key) != 1:
            raise ServerError("Reclaimer settings only support top-level keys")
        key = key[0]
    if key in ("port", "rconport", "maxplayers"):
        if len(value) != 1:
            raise ServerError("Expected one numeric value")
        try:
            number = int(value[0])
        except ValueError as exc:
            raise ServerError("Expected a numeric value") from exc
        limit = 127 if key == "maxplayers" else 65535
        minimum = 1 if key == "maxplayers" else 1024
        if not minimum <= number <= limit:
            raise ServerError(f"{key} must be between {minimum} and {limit}")
        return number
    if key == "map":
        name = " ".join(value)
        installed = Path(server.data["dir"]) / "game" / "halo3" / "maps"
        allowed = {"guardian"} | {p.stem.casefold() for p in installed.glob("*.map")
                                  if p.stem not in ("shared", "campaign")}
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or name.casefold() not in allowed:
            raise ServerError("map must be Guardian or an installed map file stem")
        return "Guardian" if name.casefold() == "guardian" else name
    if key == "rconpassword":
        password = " ".join(value)
        if not 8 <= len(password) <= 128 or any(c in password for c in "\r\n\x00"):
            raise ServerError("RCON password must contain 8 to 128 characters")
        return password
    if key == "servername":
        name = " ".join(value)
        if not 1 <= len(name) <= 48 or any(ord(c) < 32 for c in name):
            raise ServerError("servername must contain 1 to 48 printable characters")
        return name
    return gamemodule_common.handle_basic_checkvalue(server, original_key, *value,
        str_keys=("servername", "gamemode"))


def get_runtime_requirements(server):
    """Use the repository-owned Wine family and local-only RCON on host networking."""
    requirements = proton.get_runtime_requirements(server, port_definitions=PORT_DEFINITIONS, stop_mode="docker-stop")
    requirements["network_mode"] = "host"
    requirements.update(stop_signal="SIGINT", stop_timeout=30)
    return requirements


def get_platform_requirements(_server):
    return {"process": {"platforms": process_platforms, "architectures": process_architectures},
            "docker": {"operating_system": "linux"}}


def get_container_spec(server):
    """Keep owned MCC assets read-only while config, logs and Wine state persist."""
    spec = proton.get_container_spec(server, get_start_command, port_definitions=PORT_DEFINITIONS, stop_mode="docker-stop")
    spec.update(network_mode="host", ports=[], stop_signal="SIGINT", stop_timeout=30)
    if server.data.get("dir"):
        spec["mounts"].append({"source": str(Path(server.data["dir"]) / "game"),
                               "target": "/srv/server/game", "mode": "ro"})
    return spec


command_functions.update(update=install, rcon=rcon)
