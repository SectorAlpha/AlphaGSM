"""Read-only current-operator inventory; no Server construction or game hooks."""

import json
import os
from pathlib import Path
import stat

from .config import ConfigError, local_tag
from .contracts import text

MAX_SERVERS = 100
MAX_DATA_BYTES = 1024 * 1024


def number(value, minimum, maximum):
    """Coerce local numeric settings without accepting booleans or fractions."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    try:
        value = int(value)
        return value if minimum <= value <= maximum else None
    except ValueError:
        return None


def read_local(tag):
    """Extract an allowlist from one owned regular non-symlink datastore."""
    from server.server import DATAPATH, MODULE_CATALOG

    local_tag(tag)
    path = Path(DATAPATH) / (tag + ".json")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as handle:
        info = os.fstat(handle.fileno())
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode):
            raise ConfigError("Datastore must be a regular file owned by the current operator")
        if info.st_size > MAX_DATA_BYTES:
            raise ConfigError("Local datastore exceeds size limit")
        raw = handle.read(MAX_DATA_BYTES + 1)
    if len(raw) > MAX_DATA_BYTES:
        raise ConfigError("Local datastore exceeds size limit")
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("module"), str):
        raise ConfigError("Local server has no game module")
    game = MODULE_CATALOG.resolve(data["module"])
    if game not in MODULE_CATALOG.canonical_modules:
        raise ConfigError("Local server game module is not in the canonical module catalog")
    name = data.get("servername") or tag
    text(name)
    return {
        "tag": tag, "game_id": game, "name": name,
        "port": number(data.get("queryport"), 1, 65535) or number(data.get("port"), 1, 65535),
        "connect_port": number(data.get("port"), 1, 65535),
        "capacity": number(data.get("maxplayers"), 0, 100000) or 0,
        **{key: data.get(key) if isinstance(data.get(key), str) else None
           for key in ("publicip", "externalip", "hostip")},
    }


def inventory():
    """Enumerate the normal current-user namespace, excluding secret sidecars."""
    from server.server import DATAPATH

    selected, failures = [], []
    path = Path(DATAPATH)
    if not path.exists():
        return selected, failures
    for item in sorted(path.iterdir()):
        if not item.name.endswith(".json") or item.name.endswith(".secrets.json"):
            continue
        tag = item.name[:-5]
        try:
            local_tag(tag)
        except ConfigError:
            failures.append(("<invalid tag>", "Invalid local server tag"))
            continue
        try:
            if len(selected) >= MAX_SERVERS:
                raise ConfigError("At most 100 local servers can be selected")
            selected.append(read_local(tag))
        except ConfigError as exc:
            failures.append((tag, str(exc)))
        except (OSError, ValueError, RuntimeError):
            failures.append((tag, "Unreadable, unowned, symlinked or invalid local datastore"))
    return selected, failures
