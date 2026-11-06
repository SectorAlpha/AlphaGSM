# pylint: disable=unidiomatic-typecheck
"""Anonymous status queries. No Server instances, discovery, credentials or fallback.

Publication profiles stay the three games the local agent may publish. Every
other game with an anonymous status protocol can still be queried here. TCP,
UDP, and authenticated RCON are not status queries.
"""

from types import MappingProxyType
import ipaddress
from utils import query
from server.public_protocols import IPV4_ONLY, protocol_for

PROFILES = MappingProxyType({"teamfortress2": "a2s", "minecraft.vanilla": "slp", "minecraft.paper": "slp"})
_OBSERVED = frozenset({"a2s", "slp", "quake", "quake2", "quakeworld", "bedrock"})


def _bounded_text(value):
    if not isinstance(value, str):
        return ""
    return "".join(c for c in value if ord(c) >= 32)[:256]


def _with_text(result, key, value):
    text = _bounded_text(value)
    if text:
        result[key] = text
    return result


def _quake_result(raw):
    result = {"players": raw["players"], "capacity": raw["max_players"]}
    _with_text(result, "name", raw.get("name", ""))
    _with_text(result, "map", raw.get("map", ""))
    if "name" not in result:
        result["name"] = ""
    return result


def query_public(game_id, address, port, *, virtual_host=None, timeout=5.0):
    """Connect to one caller-validated numerical address, preserving SLP virtual host."""
    protocol = protocol_for(game_id)
    if protocol not in _OBSERVED:
        raise query.QueryError("Unsupported public profile")
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise query.QueryError("Public queries require a numerical address") from exc
    if type(port) is not int or not 1024 <= port <= 65535:
        raise query.QueryError("Destination port outside public profile policy")
    if not 0 < timeout <= 5:
        raise query.QueryError("Invalid public query budget")
    if protocol in IPV4_ONLY and ip.version != 4:
        if protocol == "a2s":
            raise query.QueryError("A2S public profile supports IPv4 only")
        raise query.QueryError("This public query supports IPv4 only")
    if protocol == "a2s":
        raw = query.parse_a2s_info(query.a2s_info(str(ip), port, timeout=timeout))
        if raw is None:
            raise query.QueryError("Invalid A2S statistics")
        result = {"players": raw["players"], "capacity": raw["max_players"]}
        _with_text(result, "name", raw["name"])
        _with_text(result, "map", raw["map"])
        if "name" not in result:
            result["name"] = ""
    elif protocol == "slp":
        raw = query.slp_info(str(ip), port, timeout=timeout, virtual_host=virtual_host)
        result = {"players": raw["players_online"], "capacity": raw["players_max"]}
        _with_text(result, "name", raw["description"])
        _with_text(result, "version", raw["version"])
        if "name" not in result:
            result["name"] = ""
    elif protocol == "bedrock":
        raw = query.bedrock_info(str(ip), port, timeout=timeout)
        result = {"players": raw["players_online"], "capacity": raw["players_max"]}
        _with_text(result, "name", raw.get("name", ""))
        _with_text(result, "map", raw.get("map", ""))
        _with_text(result, "version", raw.get("version", ""))
        if "name" not in result:
            result["name"] = ""
    else:
        reader = {"quake": query.quake_status, "quake2": query.quake2_status, "quakeworld": query.quakeworld_status}[
            protocol
        ]
        result = _quake_result(reader(str(ip), port, timeout=timeout))
    players, capacity = result["players"], result["capacity"]
    if type(players) is not int or type(capacity) is not int or not 0 <= players <= capacity <= 100000:
        raise query.QueryError("Invalid player counts")
    return result
