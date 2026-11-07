"""Preserving, transactional Tripwire native Workshop subscriptions."""

from copy import deepcopy
import re

from server import ServerError
import server.runtime as runtime_module
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from utils.platform_info import IS_LINUX

MAX_CONFIG_BYTES = 1024 * 1024
DOWNLOAD_MANAGER = "OnlineSubsystemSteamworks.SteamWorkshopDownload"
_ARRAY = re.compile(r"^\s*\+?([A-Za-z]+)\s*=\s*([^;]*?)(?:\s*(?://|;).*)?$", re.I)


def _sections(lines, targets):
    """Locate each controlled section, rejecting ambiguous duplicates."""
    found, current = {}, None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("[") and stripped.endswith("]")):
            continue
        if current is not None:
            found[current][1] = index
        name = stripped[1:-1].casefold()
        current = name if name in targets else None
        if current is not None:
            if current in found:
                raise ServerError("Duplicate native Workshop configuration section")
            found[current] = [index, len(lines)]
    return found


def _entry(line, key):
    match = _ARRAY.fullmatch(line.rstrip("\r\n"))
    if match and match[1].casefold() == key.casefold():
        return match[2].strip()
    if re.match(r"\s*[+!\-]?" + re.escape(key) + r"\s*=", line, re.I):
        raise ServerError("Unsupported native Workshop array directive")
    return None


def _owned_lines(previous, lines, found, subscription_section):
    """Require exact owned lines; legacy records can claim only canonical text."""
    old_ids = set(previous.get("ids", []))
    subscriptions = previous.get("subscription_lines", {
        item: "ServerSubscribedWorkshopItems=" + item + "\n" for item in old_ids
    })
    manager = previous.get("download_manager_line", (
        "DownloadManagers=" + DOWNLOAD_MANAGER + "\n"
        if previous.get("download_manager_owned", False) else None
    ))
    if (not isinstance(subscriptions, dict) or set(subscriptions) != old_ids
            or any(not isinstance(line, str) for line in subscriptions.values())):
        raise ServerError("Invalid native Workshop line ownership")
    if (bool(manager) != bool(previous.get("download_manager_owned", False))
            or manager is not None and not isinstance(manager, str)):
        raise ServerError("Invalid native Workshop line ownership")
    for section, expected in ((subscription_section.casefold(), list(subscriptions.values())),
                              ("ipdrv.tcpnetdriver", [manager] if manager else [])):
        start, end = found.get(section, (-1, -1))
        body = lines[start + 1:end] if start >= 0 else []
        if any(body.count(line) != 1 for line in expected):
            raise ServerError("Managed native Workshop line changed or was removed; restore it before applying or cleaning")
    return subscriptions, manager


def _render(original, item_ids, previous, subscription_section):
    lines = original.splitlines(keepends=True)
    targets = {subscription_section.casefold(), "ipdrv.tcpnetdriver"}
    found = _sections(lines, targets)
    owned_subscriptions, owned_manager = _owned_lines(previous, lines, found, subscription_section)
    bodies = {}
    operator_ids = set()
    manager_lines = []
    for section, (start, end) in found.items():
        body = []
        for line in lines[start + 1:end]:
            if section == subscription_section.casefold():
                value = _entry(line, "ServerSubscribedWorkshopItems")
                if value is not None:
                    if not value.isdecimal() or int(value) <= 0:
                        raise ServerError("Invalid native Workshop subscription ID")
                    if line == owned_subscriptions.get(value):
                        continue
                    operator_ids.add(value)
            else:
                value = _entry(line, "DownloadManagers")
                if value == DOWNLOAD_MANAGER:
                    if line != owned_manager:
                        manager_lines.append(line)
                    continue
            body.append(line)
        bodies[section] = body
    own_ids = [item for item in dict.fromkeys(item_ids) if item not in operator_ids]
    subscriptions = bodies.setdefault(subscription_section.casefold(), [])
    subscriptions.extend("ServerSubscribedWorkshopItems=" + item + "\n" for item in own_ids)
    transport = bodies.setdefault("ipdrv.tcpnetdriver", [])
    if manager_lines:
        transport[0:0] = manager_lines
        manager_owned = False
    elif item_ids:
        transport.insert(0, "DownloadManagers=" + DOWNLOAD_MANAGER + "\n")
        manager_owned = True
    else:
        manager_owned = False
    for section, (start, end) in sorted(found.items(), key=lambda pair: pair[1][0], reverse=True):
        lines[start + 1:end] = bodies[section]
    for section, title in ((subscription_section.casefold(), subscription_section),
                           ("ipdrv.tcpnetdriver", "IpDrv.TcpNetDriver")):
        if section not in found and bodies[section]:
            if lines and not lines[-1].endswith("\n"):
                lines[-1] += "\n"
            lines.extend(["\n[" + title + "]\n", *bodies[section]])
    return "".join(lines), {
        "ids": own_ids, "download_manager_owned": manager_owned,
        "subscription_lines": {
            item: "ServerSubscribedWorkshopItems=" + item + "\n" for item in own_ids
        },
        "download_manager_line": "DownloadManagers=" + DOWNLOAD_MANAGER + "\n" if manager_owned else None,
    }


def configure_native_workshop(server, item_ids, *, relative, section, owner, cache_relative=None):
    """Publish exact managed IDs while retaining operator subscriptions and keys."""
    if any(not isinstance(item, str) or not item.isdecimal() or int(item) <= 0 for item in item_ids):
        raise ServerError("Invalid native Workshop item ID")
    previous_mods = deepcopy(server.data.get("mods", {}))
    previous = previous_mods.get(owner, {})
    if not item_ids and not previous:
        return []
    if runtime_module.check_server_running(server):
        raise ServerError("Stop the running server before changing native Workshop subscriptions")
    path = safe_server_path(server, relative)
    existed = path.exists()
    original = b""
    if existed:
        with path.open("rb") as handle:
            original = handle.read(MAX_CONFIG_BYTES + 1)
        if len(original) > MAX_CONFIG_BYTES:
            raise ServerError("Native Workshop config exceeds 1 MiB")
    try:
        rendered, ownership = _render(original.decode("utf-8"), item_ids, previous, section)
    except UnicodeError as exc:
        raise ServerError("Native Workshop config is not UTF-8") from exc
    if len(rendered.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ServerError("Native Workshop config exceeds 1 MiB")
    if item_ids and cache_relative:
        safe_server_path(server, cache_relative).mkdir(parents=True, exist_ok=True)
    write_managed_text(server, relative, rendered)
    try:
        server.data.setdefault("mods", {})[owner] = ownership
        server.data.save()
    except (OSError, ServerError):
        if existed:
            write_managed_text(server, relative, original.decode("utf-8"))
        else:
            safe_server_path(server, relative).unlink()
        if previous_mods:
            server.data["mods"] = previous_mods
        else:
            server.data.pop("mods", None)
        raise
    return [relative] if item_ids else []


def configure_workshop(server, item_ids):
    """Activate KF2 subscriptions in the native dedicated-server Engine config."""
    return configure_native_workshop(
        server, item_ids, relative="KFGame/Config/" + (
            "LinuxServer" if IS_LINUX else "PCServer") + "-KFEngine.ini",
        section="OnlineSubsystemSteamworks.KFWorkshopSteamworks", owner="kf2_workshop",
        cache_relative="KFGame/Cache",
    )


def validate_installed_map(server, value, *, game_dir, suffix, stock):
    """Accept safe map names only when native content exists, plus the stock default."""
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", value):
        raise ServerError("Map must be a native installed map name")
    if value == stock:
        return value
    for relative in (f"{game_dir}/BrewedPC/Maps", f"{game_dir}/CookedPC/Maps",
                     f"{game_dir}/Cache"):
        root = safe_server_path(server, relative)
        for index, path in enumerate(root.rglob("*")):
            if index >= 10000:
                raise ServerError("Native map directory exceeds file limit")
            if path.name.casefold() == (value + suffix).casefold():
                safe_server_path(server, path.relative_to(server.data["dir"]).as_posix())
                if path.is_file() and path.stat().st_size:
                    return value
    raise ServerError("Map is not installed; start on the stock map to download Workshop content first")
