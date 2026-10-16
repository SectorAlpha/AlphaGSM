"""Ordered Conan PAK activation with scoped operator-preserving ownership."""

from server import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.owned_payloads import publish_owned_payloads
from server.modsupport.workshop_downloads import download_workshop_items

MODLIST = "ConanSandbox/Mods/modlist.txt"
OWNER = "conanexiles_workshop"


def _modlist(server):
    """Read a bounded native list without following symlinks."""
    path = safe_server_path(server, MODLIST)
    if not path.exists():
        return path, None
    with path.open("rb") as handle:
        raw = handle.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ServerError("Conan modlist exceeds the 1 MiB limit")
    return path, raw.decode("utf-8-sig")


def _pak_files(payloads):
    """Accept contained nonempty PAKs; retain their per-item filename order."""
    files, lines = {}, []
    for item, root in payloads.items():
        entries = []
        for path in root.rglob("*"):
            entries.append(path)
            if len(entries) > 10000:
                raise ServerError("Conan Workshop payload exceeds file limit")
        entries.sort()
        if len(entries) > 10000 or any(path.is_symlink() for path in entries):
            raise ServerError("Conan Workshop payload is too large or contains symlinks")
        paks = [path for path in entries if path.is_file() and path.suffix.lower() == ".pak"]
        if not paks or any(not path.stat().st_size for path in paks):
            raise ServerError("Conan Workshop item must contain a nonempty PAK")
        if any(path.suffix.lower() in (".ucas", ".utoc") for path in entries):
            raise ServerError("Conan IOStore mod packages have not been validated")
        for path in paks:
            relative = path.relative_to(root).as_posix()
            if any(char in relative for char in "\r\n*\\"):
                raise ServerError("Conan PAK filename is not a safe modlist entry")
            destination = f"ConanSandbox/Mods/{item}/{relative}"
            files[destination] = path
            lines.append(f"*{item}/{relative}")
    return files, lines


def configure_workshop(server, item_ids):
    """Publish desired PAKs and merge their ordered native activation entries."""
    state = server.data.setdefault("mods", {})
    had_lines = "conan_workshop_lines" in state
    previous = state.get("conan_workshop_lines", [])
    if not isinstance(previous, list) or any(not isinstance(line, str) for line in previous):
        raise ServerError("Invalid Conan Workshop ownership state")
    if not item_ids and not previous:
        return []
    path, original = _modlist(server)
    payloads = download_workshop_items(server, 440900, item_ids) if item_ids else {}
    files, lines = _pak_files(payloads)
    operator = [line for line in (original or "").splitlines() if line not in previous]
    # A pre-existing operator reference to the same item is never adopted.
    owned_lines = [line for line in lines if line not in operator]
    text = "\n".join(operator + owned_lines)
    if text:
        text += "\n"
    if len(text.encode("utf-8")) > 1024 * 1024:
        raise ServerError("Conan modlist exceeds the 1 MiB limit")
    write_managed_text(server, MODLIST, text)
    state["conan_workshop_lines"] = owned_lines
    try:
        paths = publish_owned_payloads(server, OWNER, files)
    except BaseException:
        if had_lines:
            state["conan_workshop_lines"] = previous
        else:
            state.pop("conan_workshop_lines", None)
        if original is None:
            safe_server_path(server, MODLIST).unlink(missing_ok=True)
        else:
            write_managed_text(server, MODLIST, original)
        raise
    return [MODLIST, *paths]
