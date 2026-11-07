"""Bootstrap a new stock world and synchronize native dedicated settings."""

import os
from pathlib import Path
import re
import shutil
from xml.etree import ElementTree as ET

from server import ServerError
import server.runtime as runtime_module
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from .workshop import CONFIGFILE, configured_world, read_xml


def _set(document, key, value):
    node = document.find(key)
    if node is None:
        node = ET.SubElement(document, key)
    node.text = str(value)


def _native_path(server, path):
    root = (Path(runtime_module.DEFAULT_CONTAINER_WORKDIR)
            if runtime_module.resolve_runtime_metadata(server)["runtime"] == "docker"
            else Path(server.data["dir"]).resolve())
    relative = path.relative_to(Path(server.data["dir"]).resolve())
    if os.name == "nt":
        return str(root / relative)
    return "Z:" + str(root / relative).replace("/", "\\")


def sync_server_config(server):
    """Create a missing default world once; preserve existing world data thereafter."""
    config_path = safe_server_path(server, CONFIGFILE)
    creating = not config_path.exists()
    if not creating:
        document = read_xml(config_path)
        if document.tag != "MyConfigDedicated":
            raise ServerError("Invalid Space Engineers dedicated config root")
        world = configured_world(server, document)
    else:
        stock = safe_server_path(server, "Content/CustomWorlds/Empty World")
        if not stock.exists():
            return  # Download mocks and installations not yet populated have no world template.
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", server.name):
            raise ServerError("Space Engineers default world name must be a safe folder name")
        world = safe_server_path(server, f"Saves/{server.name}")
        if world.exists():
            raise ServerError("Unowned Space Engineers world already exists; configure LoadWorld explicitly")
        for child in stock.rglob("*"):
            safe_server_path(server, child.relative_to(server.data["dir"]))
        try:
            shutil.copytree(stock, world)
            for filename in ("Sandbox.sbc", "Sandbox_config.sbc"):
                path = world / filename
                native = read_xml(path)
                _set(native, "SessionName", server.name)
                settings = native.find("Settings")
                if settings is not None:
                    _set(settings, "OnlineMode", "PUBLIC")
                    _set(settings, "MaxPlayers", server.data.get("maxplayers", 8))
                write_managed_text(server, path.relative_to(server.data["dir"]),
                                   ET.tostring(native, encoding="unicode") + "\n")
        except BaseException:
            shutil.rmtree(world, ignore_errors=True)
            raise
        document = ET.Element("MyConfigDedicated")
        ET.SubElement(document, "SessionSettings")
        _set(document.find("SessionSettings"), "OnlineMode", "PUBLIC")
        _set(document.find("SessionSettings"), "MaxPlayers", server.data.get("maxplayers", 8))
        _set(document, "WorldName", server.name)
        _set(document, "IP", "0.0.0.0")
        _set(document, "NetworkType", "steam")
        _set(document, "PauseGameWhenEmpty", "false")
        _set(document, "IgnoreLastSession", "true")
        _set(document, "AutodetectDependencies", "true")
    _set(document, "LoadWorld", _native_path(server, world))
    _set(document, "ServerPort", server.data["port"])
    _set(document, "ServerName", server.data.get("servername", f"AlphaGSM {server.name}"))
    settings = document.find("SessionSettings")
    if settings is not None and "maxplayers" in server.data:
        _set(settings, "MaxPlayers", server.data["maxplayers"])
    try:
        write_managed_text(server, CONFIGFILE, ET.tostring(document, encoding="unicode") + "\n")
    except BaseException:
        if creating:
            shutil.rmtree(world, ignore_errors=True)
        raise
