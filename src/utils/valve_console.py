"""Parse Source dedicated-server console output.

These helpers live outside ``utils.valve_server`` so that module stays under
the pylint line limit. Names are re-exported from ``utils.valve_server``.
"""

import re


_SOURCE_STATUS_PLAYERS_RE = re.compile(
    r"(?P<players>\d+) humans, (?P<bots>\d+) bots \((?P<max_players>\d+) max\)"
)
_SOURCE_BOOL_CVAR_RE = re.compile(r'"?(?P<name>[^"=]+)"?\s*=\s*"?(?P<value>[01])"?')


def parse_source_console_status(output):
    """Parse the latest Source ``status`` block from console log output."""

    lines = output.splitlines()
    status_indexes = [index for index, line in enumerate(lines) if line.strip() == "status"]
    if not status_indexes:
        status_indexes = [0]

    for start in reversed(status_indexes):
        parsed = {}
        for raw_line in lines[start + 1 :]:
            line = raw_line.strip()
            if not line:
                continue
            if line == "status" and parsed:
                break
            if line.startswith("hostname:"):
                parsed["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("version :"):
                parsed["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("udp/ip  :"):
                parsed["address"] = line.split(":", 1)[1].strip()
            elif line.startswith("map     :"):
                map_value = line.split(":", 1)[1].strip()
                parsed["map"] = map_value.split(" at:", 1)[0].strip()
            elif line.startswith("players :"):
                match = _SOURCE_STATUS_PLAYERS_RE.search(line.split(":", 1)[1].strip())
                if match is not None:
                    parsed.update(
                        {
                            "players": int(match.group("players")),
                            "bots": int(match.group("bots")),
                            "max_players": int(match.group("max_players")),
                        }
                    )
            elif line.startswith("tags    :"):
                parsed["tags"] = line.split(":", 1)[1].strip()
            elif line.startswith("steamid :"):
                parsed["steamid"] = line.split(":", 1)[1].strip()

        if {"name", "version", "map", "players", "bots", "max_players"}.issubset(parsed):
            return parsed
    return None


def parse_source_bool_cvar(output, cvar_name):
    """Parse a Source boolean cvar response from console log output."""

    for raw_line in reversed(output.splitlines()):
        line = raw_line.strip()
        if not line:
            continue
        match = _SOURCE_BOOL_CVAR_RE.search(line)
        if match is None:
            continue
        if match.group("name").strip() != cvar_name:
            continue
        return match.group("value") == "1"
    return None
