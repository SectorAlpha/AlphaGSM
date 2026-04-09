"""Module-to-runtime-family manifest used by the wrapper codemod."""

from __future__ import annotations

import copy
from fnmatch import fnmatchcase


MODULE_FAMILY_MAP = {
    "alienarenaserver": {
        "family": "steamcmd-linux",
        "port_definitions": (("port", "udp"),),
        "builder": "shared",
    },
    "minecraft.vanilla": {
        "family": "java",
        "port_definitions": (("port", "tcp"),),
        "builder": "shared",
    },
    "minecraft.bungeecord": {
        "family": "java",
        "port_definitions": (("port", "tcp"),),
        "builder": "shared",
    },
    "askaserver": {
        "family": "wine-proton",
        "port_definitions": (("port", "udp"), ("queryport", "udp")),
        "builder": "proton",
    },
}


def load_module_family_map():
    """Return a deep copy of the runtime-family manifest."""

    return copy.deepcopy(MODULE_FAMILY_MAP)


def iter_module_family_entries():
    """Yield ``(module_pattern, manifest_entry)`` pairs in manifest order."""

    for module_pattern, entry in MODULE_FAMILY_MAP.items():
        yield module_pattern, copy.deepcopy(entry)


def resolve_module_family(module_name):
    """Return the manifest entry matching *module_name*, if any."""

    if module_name in MODULE_FAMILY_MAP:
        return copy.deepcopy(MODULE_FAMILY_MAP[module_name])
    for module_pattern, entry in MODULE_FAMILY_MAP.items():
        if fnmatchcase(module_name, module_pattern):
            return copy.deepcopy(entry)
    return None


def module_patterns_for_family(family):
    """Return the manifest patterns that target *family*."""

    return tuple(
        module_pattern
        for module_pattern, entry in MODULE_FAMILY_MAP.items()
        if entry.get("family") == family
    )


def known_families():
    """Return the families represented in the manifest."""

    return tuple(sorted({entry.get("family") for entry in MODULE_FAMILY_MAP.values()}))

