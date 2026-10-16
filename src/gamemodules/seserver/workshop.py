"""Manage Steam Workshop references in the native Space Engineers world files."""

from pathlib import Path
import os
import re
from xml.etree import ElementTree as ET

from server import ServerError
import server.runtime as runtime_module
from server.modsupport.native_workshop import safe_server_path, write_managed_text

WORKSHOP_APP_ID = 244850
CONFIGFILE = "SpaceEngineers-Dedicated.cfg"


def read_xml(path):
    """Read bounded native XML without external entities."""
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ServerError("Space Engineers native XML exceeds size limit")
    raw = path.read_bytes()
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ServerError("Space Engineers XML must not declare entities")
    try:
        return ET.fromstring(raw, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    except ET.ParseError as exc:
        raise ServerError("Invalid Space Engineers native XML") from exc


def configured_world(server, config):
    """Translate a contained native LoadWorld reference to the host installation."""
    reference = (config.findtext("LoadWorld") or "").strip().replace("\\", "/")
    if not reference or reference.startswith("//"):
        raise ServerError("Space Engineers needs a contained configured world before applying mods")
    if reference.startswith("Z:"):
        reference = reference[2:]
    if ((re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", reference) and os.name != "nt")
            or ".." in Path(reference).parts):
        raise ServerError("Space Engineers world path escapes the installation")
    if reference.startswith(runtime_module.DEFAULT_CONTAINER_WORKDIR + "/"):
        reference = reference[len(runtime_module.DEFAULT_CONTAINER_WORKDIR) + 1:]
    elif Path(reference).is_absolute():
        try:
            reference = str(Path(reference).relative_to(Path(server.data["dir"]).resolve()))
        except ValueError as exc:
            raise ServerError("Space Engineers world path escapes the installation") from exc
    if reference.endswith("/Sandbox.sbc"):
        reference = reference[:-len("/Sandbox.sbc")]
    return safe_server_path(server, reference)


def _fingerprint(node):
    return ET.canonicalize(ET.tostring(node, encoding="unicode"), strip_text=True, with_comments=True)


def _mods(document):
    entries = document.findall("Mods")
    if len(entries) > 1:
        raise ServerError("Space Engineers world has ambiguous duplicate Mods elements")
    return entries[0] if entries else ET.SubElement(document, "Mods")


def apply_workshop(server, item_ids):
    """Enable Steam IDs in both world files, preserving operator entries and edits."""
    if runtime_module.check_server_running(server):
        raise ServerError("Stop the running Space Engineers server before changing Workshop mods")
    if (len(item_ids) != len(set(item_ids)) or any(
            not re.fullmatch(r"[1-9][0-9]{0,19}", item) for item in item_ids)):
        raise ServerError("Invalid or duplicate Space Engineers Workshop item IDs")
    previous = server.data.get("spaceengineers_workshop")
    if not item_ids and not previous:
        return []
    config = read_xml(safe_server_path(server, CONFIGFILE))
    if config.tag != "MyConfigDedicated":
        raise ServerError("Invalid Space Engineers dedicated config root")
    world = configured_world(server, config)
    documents, originals = {}, {}
    targets = [world / "Sandbox.sbc", world / "Sandbox_config.sbc"] if item_ids else []
    all_paths = list(dict.fromkeys([*(entry["path"] for entry in previous or []),
                                    *(path.relative_to(server.data["dir"]).as_posix() for path in targets)]))
    for relative in all_paths:
        path = safe_server_path(server, relative)
        originals[relative] = path.read_text(encoding="utf-8")
        document = read_xml(path)
        expected = ("MyObjectBuilder_Checkpoint" if path.name == "Sandbox.sbc"
                    else "MyObjectBuilder_WorldConfiguration")
        if document.tag != expected:
            raise ServerError("Invalid Space Engineers world config root")
        documents[relative] = document
    for entry in previous or []:
        mods = _mods(documents[entry["path"]])
        for owned in entry["items"]:
            matches = [node for node in mods if node.tag == "ModItem"
                       and node.findtext("PublishedFileId") == owned["id"]
                       and node.findtext("PublishedServiceName", "Steam") == "Steam"]
            if any(_fingerprint(node) != owned["xml"] for node in matches):
                raise ServerError("Managed Space Engineers mod changed externally; preserving it")
            for node in matches:
                mods.remove(node)
    additions = []
    for path in targets:
        relative = path.relative_to(server.data["dir"]).as_posix()
        mods = _mods(documents[relative])
        records = []
        for item in item_ids:
            if any(node.findtext("PublishedFileId") == item
                   and node.findtext("PublishedServiceName", "Steam") == "Steam" for node in mods):
                raise ServerError("Unowned Space Engineers Workshop item is already configured")
            node = ET.SubElement(mods, "ModItem", Name=f"{item}.sbm")
            ET.SubElement(node, "PublishedFileId").text = item
            ET.SubElement(node, "PublishedServiceName").text = "Steam"
            records.append({"id": item, "xml": _fingerprint(node)})
        additions.append({"path": relative, "items": records})
    try:
        for relative, document in documents.items():
            write_managed_text(server, relative, ET.tostring(document, encoding="unicode") + "\n")
        server.data["spaceengineers_workshop"] = additions
        server.data.save()
    except BaseException:
        for relative, text in originals.items():
            write_managed_text(server, relative, text)
        if previous is None:
            server.data.pop("spaceengineers_workshop", None)
        else:
            server.data["spaceengineers_workshop"] = previous
        server.data.save()
        raise
    return list(documents)
