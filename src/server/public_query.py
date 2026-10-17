# pylint: disable=unidiomatic-typecheck
"""Reviewed public profiles; no Server instances, discovery, credentials or fallback."""

from types import MappingProxyType
import ipaddress
from utils import query

PROFILES = MappingProxyType({"teamfortress2": "a2s", "minecraft.vanilla": "slp", "minecraft.paper": "slp"})


def _bounded_text(value):
    if not isinstance(value, str):
        return ""
    return "".join(c for c in value if ord(c) >= 32)[:256]


def query_public(game_id, address, port, *, virtual_host=None, timeout=5.0):
    """Connect to one caller-validated numerical address, preserving SLP virtual host."""
    if type(game_id) is not str or game_id not in PROFILES:
        raise query.QueryError("Unsupported public profile")
    try:
        ip = ipaddress.ip_address(address)
    except ValueError as exc:
        raise query.QueryError("Public queries require a numerical address") from exc
    if type(port) is not int or not 1024 <= port <= 65535:
        raise query.QueryError("Destination port outside public profile policy")
    if not 0 < timeout <= 5:
        raise query.QueryError("Invalid public query budget")
    if PROFILES[game_id] == "a2s":
        if ip.version != 4:
            raise query.QueryError("A2S public profile supports IPv4 only")
        raw = query.parse_a2s_info(query.a2s_info(str(ip), port, timeout=timeout))
        if raw is None:
            raise query.QueryError("Invalid A2S statistics")
        result = {
            "name": _bounded_text(raw["name"]),
            "map": _bounded_text(raw["map"]),
            "players": raw["players"],
            "capacity": raw["max_players"],
        }
    else:
        raw = query.slp_info(str(ip), port, timeout=timeout, virtual_host=virtual_host)
        result = {
            "name": _bounded_text(raw["description"]),
            "players": raw["players_online"],
            "capacity": raw["players_max"],
            "version": _bounded_text(raw["version"]),
        }
    players, capacity = result["players"], result["capacity"]
    if type(players) is not int or type(capacity) is not int or not 0 <= players <= capacity <= 100000:
        raise query.QueryError("Invalid player counts")
    return result
