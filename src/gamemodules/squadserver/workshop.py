"""Squad-family native Unreal plugin staging with exact file ownership."""

import json
import configparser

from server import ServerError
from server.modsupport.owned_payloads import publish_owned_payloads
from server.modsupport.workshop_downloads import download_workshop_items


def _plugin_files(payloads, game_dir):
    """Require valid content plugins and native Linux cooked assets."""
    files = {}
    for item, root in payloads.items():
        entries = []
        for path in root.rglob("*"):
            entries.append(path)
            if len(entries) > 10000:
                raise ServerError("Unreal Workshop plugin exceeds file limit")
        entries.sort()
        if len(entries) > 10000 or root.is_symlink() or any(path.is_symlink() for path in entries):
            raise ServerError("Unreal Workshop plugin contains symlinks or exceeds file limit")
        descriptors = [path for path in entries if path.suffix == ".uplugin" and path.is_file()]
        if not descriptors:
            raise ServerError("Workshop item has no Unreal plugin descriptor")
        for descriptor in descriptors:
            with descriptor.open("rb") as handle:
                raw = handle.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ServerError("Unreal plugin descriptor exceeds size limit")
            try:
                metadata = json.loads(raw.decode("utf-8-sig"))
                valid = (isinstance(metadata, dict) and metadata.get("FileVersion") == 3
                         and metadata.get("CanContainContent") is True)
            except (ValueError, UnicodeError) as exc:
                raise ServerError("Invalid Unreal plugin descriptor") from exc
            if not valid:
                raise ServerError("Workshop item is not a supported Unreal content plugin")
            mod_info = descriptor.with_suffix(".mi")
            if not mod_info.is_file() or mod_info.is_symlink():
                raise ServerError("Unreal plugin has no bounded native mod identity")
            with mod_info.open("rb") as handle:
                raw_info = handle.read(1024 * 1024 + 1)
            if len(raw_info) > 1024 * 1024:
                raise ServerError("Unreal plugin native mod identity exceeds size limit")
            parser = configparser.RawConfigParser()
            try:
                parser.read_string(raw_info.decode("utf-8-sig"))
                identity = parser.get("Modding.Core", "ID")
            except (configparser.Error, UnicodeError) as exc:
                raise ServerError("Invalid native Unreal mod identity") from exc
            if identity != item:
                raise ServerError("Unreal mod identity differs from its Workshop item")
            cooked = descriptor.parent / "Content/Paks"
            if not any(path.is_file() and path.suffix == ".pak" and path.stat().st_size
                       and any(part.startswith("Linux") for part in path.relative_to(cooked).parts)
                       for path in entries if cooked in path.parents):
                raise ServerError("Unreal plugin has no native Linux cooked PAK")
        for path in entries:
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if any(part.startswith("Windows") or part.startswith("Mac") for part in relative.parts):
                continue
            files[f"{game_dir}/Plugins/Mods/{item}/{relative.as_posix()}"] = path
    return files


def configure_plugin_workshop(server, app_id, game_dir, owner, item_ids):
    """Publish complete validated plugins; the engine discovers them at startup."""
    if not item_ids and not server.data.get("mods", {}).get("owned_payloads", {}).get(owner):
        return []
    payloads = download_workshop_items(server, app_id, item_ids) if item_ids else {}
    return publish_owned_payloads(server, owner, _plugin_files(payloads, game_dir))


def configure_workshop(server, item_ids):
    """Stage Squad's native plugins under its Plugins/Mods directory."""
    return configure_plugin_workshop(server, 393380, "SquadGame", "squad_workshop", item_ids)
