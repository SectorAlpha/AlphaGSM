"""Publish anonymous Wreckfest Workshop assets through native mod folders."""

import os
from pathlib import Path
import re

from server.errors import ServerError
import server.runtime as runtime_module
from server.modsupport import owned_payloads
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop_downloads import download_workshop_items

WORKSHOP_APP_ID = 228380
OWNER = "wreckfestserver"


def _files(server, item, source):
    root = Path(server.data["dir"]).resolve()
    try:
        relative = source.absolute().relative_to(root)
    except ValueError as exc:
        raise ServerError("Wreckfest payload is outside the server root") from exc
    safe_server_path(server, relative)
    files = {}
    for index, (directory, subdirs, names) in enumerate(os.walk(source, followlinks=False)):
        if index >= 4096:
            raise ServerError("Wreckfest payload exceeds directory limit")
        if any((Path(directory) / name).is_symlink() for name in subdirs + names):
            raise ServerError("Refusing symlinked Wreckfest Workshop content")
        for name in names:
            path = Path(directory) / name
            if path.suffix.lower() in (".exe", ".dll", ".so", ".bat", ".cmd", ".ps1"):
                raise ServerError("Wreckfest native assets must not contain executable plugins")
            files[f"mods/alphagsm-{item}/{path.relative_to(source).as_posix()}"] = path
    metadata = source / "modinfo.modi"
    if not metadata.is_file() or metadata.stat().st_size > 4 * 1024 * 1024:
        raise ServerError("Wreckfest item needs a bounded native modinfo.modi")
    with metadata.open("rb") as handle:
        header = handle.read(8)
    if header[4:8] != b"idom":
        raise ServerError("Invalid native Wreckfest modinfo.modi signature")
    if not any(key.startswith(f"mods/alphagsm-{item}/data/") for key in files):
        raise ServerError("Wreckfest item has no native data assets")
    return files


def _configuration(text):
    lines = text.splitlines(keepends=True)
    indices = [index for index, line in enumerate(lines)
               if re.match(r"^\s*mods\s*=", line, re.IGNORECASE)]
    if len(indices) > 1:
        raise ServerError("Refusing duplicate native Wreckfest mods keys")
    if not indices:
        return lines, None, [], "mods=", ""
    index = indices[0]
    prefix, value = lines[index].rstrip("\r\n").split("=", 1)
    value, separator, comment = value.partition("#")
    folders = [entry.strip() for entry in value.split(",") if entry.strip()]
    if any(not re.fullmatch(r"[A-Za-z0-9_. -]{1,128}", folder) or folder in (".", "..") for folder in folders):
        raise ServerError("Unsafe native Wreckfest mod folder")
    return lines, index, folders, prefix + "=", (" #" + comment if separator else "")


def apply_workshop(server, item_ids):
    """Preserve operator mod order and settings; remove only our tracked entries."""
    if runtime_module.check_server_running(server):
        raise ServerError("Stop the running Wreckfest server before changing Workshop mods")
    relative = server.data.get("configfile", "server_config.cfg")
    config = safe_server_path(server, relative)
    if config.exists() and config.stat().st_size > 1024 * 1024:
        raise ServerError("Wreckfest server configuration exceeds size limit")
    original = config.read_text(encoding="utf-8") if config.exists() else None
    lines, index, folders, prefix, comment = _configuration(original or "")
    previous = server.data.get("wreckfest_workshop")
    owned = (previous or {}).get("folders", [])
    if previous and previous.get("path") != str(relative):
        raise ServerError("Clean up Wreckfest Workshop entries before changing configfile")
    operator = [folder for folder in folders if folder not in owned]
    desired = [f"alphagsm-{item}" for item in item_ids]
    if any(folder in operator for folder in desired):
        raise ServerError("Unowned Wreckfest native mod folder is already configured")
    downloaded = download_workshop_items(server, WORKSHOP_APP_ID, item_ids) if item_ids else {}
    files = {}
    for item in item_ids:
        files.update(_files(server, item, downloaded[item]))
    replacement = prefix + ",".join(operator + desired) + comment + "\n"
    had_mods = (previous or {}).get("had_mods", index is not None)
    if index is None:
        if desired:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.append(replacement)
    elif not desired and not operator and not had_mods and not comment:
        lines.pop(index)
    else:
        lines[index] = replacement
    if not desired and not owned:
        return []
    write_managed_text(server, relative, "".join(lines))
    server.data["wreckfest_workshop"] = {"path": str(relative), "folders": desired, "had_mods": had_mods}
    try:
        paths = owned_payloads.publish_owned_payloads(server, OWNER, files)
    except BaseException:
        if previous is None:
            server.data.pop("wreckfest_workshop", None)
        else:
            server.data["wreckfest_workshop"] = previous
        if original is None:
            config.unlink(missing_ok=True)
        else:
            write_managed_text(server, relative, original)
        server.data.save()
        raise
    return [str(relative), *paths]
