"""Explicit native endpoint diagnostics; never run as a publication renewal hook."""

import ipaddress
import time

from server.public_query import IPV4_ONLY, protocol_for, query_public
from .dns_lookup import DNS_TIMEOUT, PreflightError, resolve_host
from .inventory import read_local
from .network import suggest_public_host
from .preflight import expected_addresses, matched_addresses, numerical
from .publication_config import normalize_public_ips

PROBE_TIMEOUT = 5.0


def check_endpoint(binding, expected_public_ips=None, *, resolve=None, probe=None, read=None, discover=None):
    """Probe only validated pinned machine IPs, retaining SLP's original host."""
    metadata = binding['metadata']
    game, host, port = metadata['game_id'], metadata['host'], metadata['port']
    protocol = protocol_for(game)
    if protocol is None:
        raise PreflightError("This game has no supported public query profile; private binding remains available")
    if protocol == "ts3":
        if type(port) is not int or port != 10011:  # pylint: disable=unidiomatic-typecheck
            raise PreflightError("TeamSpeak checks use query port 10011")
    elif type(port) is not int or not 1024 <= port <= 65535:  # pylint: disable=unidiomatic-typecheck
        raise PreflightError("Public endpoint checks require an advertised port from 1024 to 65535")
    selected = dict(binding)
    if expected_public_ips is not None:
        selected['expected_public_ips'] = normalize_public_ips(expected_public_ips)
    expected = expected_addresses(selected, [], read=read or read_local, discover=discover or suggest_public_host)
    if numerical(host):
        answers = [host]
    else:
        dns_deadline = time.monotonic() + DNS_TIMEOUT
        try:
            answers = (resolve or resolve_host)(host, DNS_TIMEOUT)
        except (OSError, ValueError, RuntimeError):
            raise PreflightError("DNS unavailable or timed out; no endpoint connection was attempted") from None
        if time.monotonic() >= dns_deadline:
            raise PreflightError("DNS lookup timed out; no endpoint connection was attempted")
    addresses = matched_addresses(answers, expected)
    if protocol in IPV4_ONLY and any(ipaddress.ip_address(address).version != 4 for address in addresses):
        raise PreflightError("This public query supports IPv4 only; check the hostname AAAA record")
    deadline = time.monotonic() + PROBE_TIMEOUT
    for address in addresses:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PreflightError("Public endpoint check timed out; check the advertised port and NAT loopback support")
        try:
            (probe or query_public)(game, address, port, virtual_host=host, timeout=remaining)
        except (OSError, ValueError, RuntimeError):
            raise PreflightError("Public endpoint unavailable; check the server, advertised port, firewall and NAT loopback support") from None
        if time.monotonic() > deadline:
            raise PreflightError("Public endpoint check timed out; check the advertised port and NAT loopback support")
    return addresses
