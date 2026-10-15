"""Optional local machine-address expectations, excluded from agent wire metadata."""

import ipaddress

class PublicationConfigError(ValueError):
    """Invalid local expected-machine address selection."""


MAX_PUBLIC_IPS = 32


def public_ip(value):
    if not isinstance(value, str) or '%' in value:
        return None
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return None
    if not parsed.is_global or parsed.is_multicast or parsed.is_reserved or parsed.is_unspecified:
        return None
    if isinstance(parsed, ipaddress.IPv6Address) and (parsed.ipv4_mapped or parsed.sixtofour or parsed.teredo):
        return None
    return str(parsed)


def normalize_public_ips(value):
    if type(value) is not list or not 1 <= len(value) <= MAX_PUBLIC_IPS:  # pylint: disable=unidiomatic-typecheck
        raise PublicationConfigError("Use --public-ip with one or more global numerical machine IPs")
    selected = [public_ip(address) for address in value]
    if any(address is None for address in selected):
        raise PublicationConfigError("Expected machine IPs must be globally routable numerical unicast addresses")
    return sorted(set(selected))


def local_publication(provided=None, previous=None):
    if provided is None and previous is not None:
        provided = previous.get('expected_public_ips')
    return {} if provided is None else {'expected_public_ips': normalize_public_ips(provided)}
