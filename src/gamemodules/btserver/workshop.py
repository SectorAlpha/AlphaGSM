"""Activate validated XML Workshop packages through Barotrauma's native loader."""

import os
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from server.errors import ServerError
from server.modsupport import owned_payloads
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop_downloads import download_workshop_items

WORKSHOP_APP_ID = 602960
OWNER = "btserver"
MAX_XML_BYTES = 4 * 1024 * 1024


def _xml(path):
    if path.stat().st_size > MAX_XML_BYTES:
        raise ServerError("Barotrauma XML exceeds the metadata size limit")
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ServerError("Barotrauma XML must not declare entities")
    try:
        return ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    except ET.ParseError as exc:
        raise ServerError(f"Invalid Barotrauma XML: {path.name}") from exc


def _files(server, source, destination):
    root = Path(server.data["dir"]).resolve()
    try:
        relative = source.absolute().relative_to(root)
    except ValueError as exc:
        raise ServerError("Barotrauma Workshop payload is outside server root") from exc
    safe_server_path(server, relative)
    files = {}
    for index, (directory, subdirs, filenames) in enumerate(os.walk(source, followlinks=False)):
        if index >= 4096:
            raise ServerError("Barotrauma Workshop payload exceeds directory limit")
        for name in subdirs + filenames:
            if (Path(directory) / name).is_symlink():
                raise ServerError("Refusing symlinked Barotrauma Workshop payload")
        for name in filenames:
            path = Path(directory) / name
            if path.suffix.lower() in (".dll", ".exe", ".so", ".lua"):
                raise ServerError("Barotrauma native support requires XML packages; Lua/CSharp need a separate executable")
            files[f"{destination}/{path.relative_to(source).as_posix()}"] = path
    return files


def _validate_paths(server, document, source):
    for element in document.iter():
        for key, value in element.attrib.items():
            if key.lower() not in ("file", "texture", "sound", "sprite", "path"):
                continue
            value = value.replace("\\", "/")
            if not value or (key.lower() == "path" and element is document
                             and document.tag.lower() == "contentpackage"):
                continue
            path = value.removeprefix("%ModDir%/")
            if Path(path).is_absolute() or ".." in Path(path).parts or re.match(r"^[A-Za-z]:", path):
                raise ServerError("Unsafe Barotrauma package content path")
            if "%" in path:
                raise ServerError("Cross-package Barotrauma path macros are not supported")
            if value.startswith("Content/"):
                safe_server_path(server, value)
            elif key.lower() == "file":
                if not (source / path).is_file():
                    raise ServerError(f"Barotrauma package references missing content: {value}")


def _package(server, item, source):
    destination = f"LocalMods/alphagsm-{item}"
    files = _files(server, source, destination)
    metadata = source / "filelist.xml"
    if not metadata.is_file():
        raise ServerError("Barotrauma Workshop item needs a root filelist.xml")
    document = _xml(metadata)
    name = document.get("name", "").strip()
    if document.tag.lower() != "contentpackage" or not name:
        raise ServerError("Barotrauma Workshop item has invalid package metadata")
    if document.get("corepackage", "false").lower() != "false":
        raise ServerError("Barotrauma core replacements require deliberate operator configuration")
    if document.get("steamworkshopid", item) != item:
        raise ServerError("Barotrauma package Workshop identity differs from requested item")
    _validate_paths(server, document, source)
    for path in files.values():
        if path.suffix.lower() == ".xml" and path != metadata:
            _validate_paths(server, _xml(path), source)
    for element in document:
        value = element.get("file", "")
        if value and not value.startswith(("%ModDir%/", "Content/")):
            element.set("file", f"%ModDir%/{value}")
    files[f"{destination}/filelist.xml"] = ET.tostring(document, encoding="utf-8")
    return {"name": name, "path": f"{destination}/filelist.xml"}, files


def apply_workshop(server, item_ids):
    """Preserve operator XML entries, and own only native entries we add."""
    config = safe_server_path(server, "config_player.xml")
    root = _xml(config) if config.exists() else ET.Element("config")
    packages = root.find("contentpackages")
    if packages is None:
        packages = ET.SubElement(root, "contentpackages")
    if packages.find("corepackage") is None:
        ET.SubElement(packages, "corepackage", path="Content/ContentPackages/Vanilla.xml")
    regular = packages.find("regularpackages")
    if regular is None:
        regular = ET.SubElement(packages, "regularpackages")
    prior = server.data.get("barotrauma_workshop", [])
    for entry in prior:
        matching = [node for node in regular if node.get("path") == entry["path"]]
        if any(dict(node.attrib) != entry for node in matching):
            raise ServerError("Managed Barotrauma native entry changed externally; preserving it")
        for node in matching:
            regular.remove(node)
    files, additions = {}, []
    downloaded = download_workshop_items(server, WORKSHOP_APP_ID, item_ids) if item_ids else {}
    names = {node.get("name") for node in regular}
    for item in item_ids:
        entry, payload = _package(server, item, downloaded[item])
        if entry["name"] in names:
            raise ServerError("Barotrauma package name conflicts with another configured package")
        names.add(entry["name"])
        ET.SubElement(regular, "package", **entry)
        additions.append(entry)
        files.update(payload)
    previous_text = config.read_text(encoding="utf-8") if config.exists() else None
    previous_entries = server.data.get("barotrauma_workshop")
    write_managed_text(server, "config_player.xml", ET.tostring(root, encoding="unicode") + "\n")
    server.data["barotrauma_workshop"] = additions
    try:
        owned_payloads.publish_owned_payloads(server, OWNER, files)
    except BaseException:
        if previous_entries is None:
            server.data.pop("barotrauma_workshop", None)
        else:
            server.data["barotrauma_workshop"] = previous_entries
        if previous_text is None:
            safe_server_path(server, "config_player.xml").unlink(missing_ok=True)
        else:
            write_managed_text(server, "config_player.xml", previous_text)
        server.data.save()
        raise
    server.data.save()
    return ["config_player.xml"]
