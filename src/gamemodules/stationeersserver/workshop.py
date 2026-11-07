"""Activate native Stationeers XML gameplay packages without a plugin loader."""

import os
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from server.errors import ServerError
import server.runtime as runtime_module
from server.modsupport import owned_payloads
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop_downloads import download_workshop_items

WORKSHOP_APP_ID = 544550
OWNER = "stationeersserver"


def _xml(path):
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ServerError("Stationeers XML exceeds size limit")
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ServerError("Stationeers XML must not declare entities")
    try:
        return ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    except ET.ParseError as exc:
        raise ServerError("Invalid Stationeers XML metadata") from exc


def _files(server, item, source):
    root = Path(server.data["dir"]).resolve()
    try:
        relative = source.absolute().relative_to(root)
    except ValueError as exc:
        raise ServerError("Stationeers Workshop payload is outside server root") from exc
    safe_server_path(server, relative)
    files, data_files = {}, []
    for index, (directory, subdirs, names) in enumerate(os.walk(source, followlinks=False)):
        if index >= 4096:
            raise ServerError("Stationeers package exceeds directory limit")
        if any((Path(directory) / name).is_symlink() for name in subdirs + names):
            raise ServerError("Refusing symlinked Stationeers Workshop payload")
        for name in names:
            path = Path(directory) / name
            if path.suffix.lower() in (".dll", ".exe", ".so", ".lua", ".cs", ".bat", ".cmd", ".ps1"):
                raise ServerError("Stationeers code mods need a separate supported plugin loader")
            destination = path.relative_to(source)
            files[f"mods/alphagsm-{item}/{destination.as_posix()}"] = path
            if destination.parts[0] == "GameData" and path.suffix.lower() == ".xml":
                data_files.append(path)
    about = source / "About/About.xml"
    if not about.is_file():
        raise ServerError("Stationeers package needs About/About.xml metadata")
    metadata = _xml(about)
    if metadata.tag != "ModMetadata" or not metadata.findtext("Name", "").strip():
        raise ServerError("Invalid Stationeers package metadata")
    if metadata.findtext("WorkshopHandle", "").strip() != item:
        raise ServerError("Stationeers native Workshop identity differs from requested item")
    if not data_files:
        raise ServerError("Stationeers native support requires GameData XML gameplay content")
    for path in data_files:
        document = _xml(path)
        if document.tag != "GameData":
            raise ServerError("Stationeers package requires native GameData XML")
        for element in document.iter():
            candidates = [(element.tag, element.text or ""), *element.attrib.items()]
            for key, value in candidates:
                if not isinstance(key, str) or not re.search(r"(?:path|file)$", key, re.IGNORECASE):
                    continue
                value = value.strip().replace("\\", "/")
                if (Path(value).is_absolute() or ".." in Path(value).parts
                        or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value)
                        or "%" in value):
                    raise ServerError("Unsafe Stationeers XML asset path")
    return files


def _fingerprint(node):
    path = node.find("Path")
    return {"attributes": dict(node.attrib), "path": dict(path.attrib) if path is not None else {},
            "xml": ET.canonicalize(ET.tostring(node, encoding="unicode"), strip_text=True, with_comments=True)}


def apply_workshop(server, item_ids):
    """Use the native batch-mode root modconfig, retaining operator XML entries."""
    config = safe_server_path(server, "modconfig.xml")
    original = config.read_text(encoding="utf-8") if config.exists() else None
    document = _xml(config) if config.exists() else ET.Element("ModConfig")
    if document.tag != "ModConfig":
        raise ServerError("Stationeers native modconfig.xml needs a ModConfig root")
    previous = server.data.get("stationeers_workshop")
    for entry in previous or []:
        matches = [node for node in document if node.tag == "Local" and node.find("Path") is not None
                   and node.find("Path").get("Value") == entry["path"]["Value"]]
        if any(_fingerprint(node) != entry for node in matches):
            raise ServerError("Managed Stationeers entry changed externally; preserving it")
        for node in matches:
            document.remove(node)
    if not item_ids and not previous:
        return []
    existing = {node.find("Path").get("Value") for node in document if node.find("Path") is not None}
    downloaded = download_workshop_items(server, WORKSHOP_APP_ID, item_ids) if item_ids else {}
    additions, files = [], {}
    native_root = (Path(runtime_module.DEFAULT_CONTAINER_WORKDIR)
                   if runtime_module.resolve_runtime_metadata(server)["runtime"] == "docker"
                   else Path(server.data["dir"]).resolve())
    for index, item in enumerate(item_ids):
        destination = f"mods/alphagsm-{item}"
        native_path = str(native_root / destination)
        aliases = {destination, native_path, str(Path(server.data["dir"]).resolve() / destination),
                   str(Path(runtime_module.DEFAULT_CONTAINER_WORKDIR) / destination)}
        if aliases.intersection(existing):
            raise ServerError("Unowned Stationeers mod folder is already configured")
        files.update(_files(server, item, downloaded[item]))
        node = ET.Element("Local", Enabled="true")
        ET.SubElement(node, "Path", Value=native_path)
        document.insert(index, node)
        additions.append(_fingerprint(node))
    if document.find("Core") is None:
        ET.SubElement(document, "Core", Enabled="true")
    write_managed_text(server, "modconfig.xml", ET.tostring(document, encoding="unicode") + "\n")
    server.data["stationeers_workshop"] = additions
    try:
        paths = owned_payloads.publish_owned_payloads(server, OWNER, files)
    except BaseException:
        if previous is None:
            server.data.pop("stationeers_workshop", None)
        else:
            server.data["stationeers_workshop"] = previous
        if original is None:
            config.unlink(missing_ok=True)
        else:
            write_managed_text(server, "modconfig.xml", original)
        server.data.save()
        raise
    return ["modconfig.xml", *paths]
