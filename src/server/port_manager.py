"""Shared helpers for discovering and validating claimed server ports."""

from __future__ import annotations

import errno
import copy
from dataclasses import dataclass
from importlib import import_module
import os
import socket
import sys
from types import SimpleNamespace

from utils.settings import settings

from . import data as data_module
from .errors import ServerError
from . import runtime as runtime_module


LOCAL_WILDCARD_IP = "0.0.0.0"
EXTERNAL_IP_KEYS = ("publicip", "externalip", "hostip")
_WILDCARD_IPS = {LOCAL_WILDCARD_IP, "::"}
_LOCAL_IPS = _WILDCARD_IPS | {"127.0.0.1", "::1"}
DATAPATH = os.path.expanduser(
    settings.user.getsection("server").get(
        "datapath",
        os.path.join(
            settings.user.getsection("core").get("alphagsm_path", "~/.alphagsm"),
            "conf",
        ),
    )
)
SERVERMODULEPACKAGE = settings.system.getsection("server").get(
    "servermodulespackage", "gamemodules."
)


@dataclass(frozen=True)
class PortEndpoint:
    """A single claimed host/port pair."""

    scope: str
    ip: str
    port: int
    source_key: str
    derived: bool = False
    shiftable: bool = True


@dataclass(frozen=True)
class PortClaimSet:
    """The full claim set collected for a server."""

    server_name: str
    endpoints: tuple[PortEndpoint, ...]
    shift_group_keys: tuple[str, ...]


@dataclass(frozen=True)
class PortConflict:
    """A single port conflict discovered while validating a claim set."""

    kind: str
    endpoint: PortEndpoint
    message: str
    managed_server: str | None = None


@dataclass(frozen=True)
class PortShiftRecommendation:
    """A whole-group shift recommendation for a server port set."""

    offset: int
    values: dict[str, int]


def is_port_key(key):
    """Return whether *key* looks like a port-bearing datastore field."""

    lowered = str(key).strip().lower()
    return lowered == "port" or lowered.endswith("port")


def normalize_hosted_ip(value, *, default=LOCAL_WILDCARD_IP):
    """Normalize host-like values into a canonical string."""

    if value in (None, ""):
        return default
    value = str(value).strip().lower()
    if value == "localhost":
        return "127.0.0.1"
    return value


def hosted_ips_overlap(left, right):
    """Return whether two normalized host selectors can address the same host."""

    left = normalize_hosted_ip(left)
    right = normalize_hosted_ip(right)
    return left == right or left in _WILDCARD_IPS or right in _WILDCARD_IPS


def _is_local_or_wildcard_ip(value):
    """Return whether *value* is a local or wildcard host selector."""

    return normalize_hosted_ip(value) in _LOCAL_IPS


def _get_module_hook(module, hook_name):
    """Return a callable hook from a module or its shared MODULE namespace."""

    for owner in (module, getattr(module, "MODULE", None)):
        hook = getattr(owner, hook_name, None)
        if callable(hook):
            return hook
    return None


def _resolve_module_name(module_name):
    """Resolve *module_name* via AlphaGSM's own module lookup path."""

    if not module_name:
        return None
    server_module = sys.modules.get("server.server")
    if server_module is not None and hasattr(server_module, "find_module"):
        try:
            _resolved_name, module = server_module.find_module(module_name)
        except (ServerError, ImportError):
            return None
        return module
    return _resolve_module_name_fallback(str(module_name))


def _resolve_module_name_fallback(name):
    """Resolve a module name recursively when the canonical server resolver is unavailable."""

    try:
        module = import_module(SERVERMODULEPACKAGE + name)
    except ImportError:
        return None
    if not hasattr(module, "__file__"):
        return _resolve_module_name_fallback(name + ".DEFAULT")
    alias_target = getattr(module, "ALIAS_TARGET", None)
    if alias_target:
        return _resolve_module_name_fallback(alias_target)
    runtime_module.ensure_runtime_hooks(module)
    return module


def _load_server_module(server):
    """Return the server module, loading it from datastore metadata if needed."""

    module = getattr(server, "module", None)
    if module is not None:
        return module
    data = getattr(server, "data", None)
    if data is None:
        return None
    module_name = getattr(data, "get", lambda *_: None)("module")
    return _resolve_module_name(module_name)


def _normalize_port_value(value):
    """Convert *value* to an integer port, returning ``None`` on failure."""

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _add_endpoint(endpoints, endpoint):
    """Append *endpoint* while preserving duplicates for conflict detection."""

    endpoints.append(endpoint)


def _hook_endpoint(server, module, hook_name, payload, existing_endpoints):
    """Return hook-derived endpoints when the hook reports a local listener."""

    hook = _get_module_hook(module, hook_name)
    if hook is None:
        return ()
    try:
        address = hook(server)
    except (AttributeError, FileNotFoundError, KeyError, RuntimeError, TypeError, ValueError):
        return ()
    if not isinstance(address, (list, tuple)) or len(address) < 2:
        return ()

    host = normalize_hosted_ip(address[0])
    port = _normalize_port_value(address[1])
    if port is None:
        return ()
    if not _is_local_or_wildcard_ip(host):
        return ()
    candidate = PortEndpoint(
        "internal",
        host,
        port,
        f"hook:{hook_name}",
        derived=True,
        shiftable=False,
    )
    if _endpoint_is_covered(existing_endpoints, candidate):
        return ()

    return (candidate,)


def _scope_ips_overlap(scope, left, right):
    """Return whether two addresses overlap for the given scope."""

    left = normalize_hosted_ip(left)
    right = normalize_hosted_ip(right)
    if scope == "internal":
        return left == right or left in _WILDCARD_IPS or right in _WILDCARD_IPS
    return left == right


def _endpoint_is_covered(endpoints, candidate):
    """Return whether *candidate* is already claimed by an existing endpoint."""

    for endpoint in endpoints:
        if endpoint.scope != candidate.scope:
            continue
        if endpoint.port != candidate.port:
            continue
        if _scope_ips_overlap(candidate.scope, endpoint.ip, candidate.ip):
            return True
    return False


def _runtime_port_endpoints(server, module, payload, allow_stale_saved_ports):
    """Return runtime/container-derived port claims for *server*."""

    from . import runtime as runtime_module

    temp_server = SimpleNamespace(
        name=getattr(server, "name", "<unknown>"),
        data=payload,
        module=module,
    )
    try:
        spec = runtime_module.get_container_spec(temp_server)
    except (
        AttributeError,
        FileNotFoundError,
        ServerError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        spec = None

    endpoints = []
    port_specs = (spec or {}).get("ports", ()) if spec is not None else ()
    if port_specs:
        for entry in port_specs:
            if not isinstance(entry, dict):
                continue
            host_port = _normalize_port_value(entry.get("host"))
            if host_port is None:
                continue
            candidate = PortEndpoint(
                "external",
                payload["external_ip"],
                host_port,
                "runtime:ports",
                derived=True,
                shiftable=False,
            )
            if not _endpoint_is_covered(endpoints, candidate):
                _add_endpoint(endpoints, candidate)
        return endpoints

    if not allow_stale_saved_ports:
        return endpoints

    for entry in payload.get("ports", ()):
        if not isinstance(entry, dict):
            continue
        host_port = _normalize_port_value(entry.get("host"))
        if host_port is None:
            continue
        candidate = PortEndpoint(
            "external",
            payload["external_ip"],
            host_port,
            "runtime:ports",
            derived=True,
            shiftable=False,
        )
        if not _endpoint_is_covered(endpoints, candidate):
            _add_endpoint(endpoints, candidate)
    return endpoints


def collect_claim_set(server, overrides=None):
    """Collect the claim set for *server*, applying optional overrides first."""

    payload = copy.deepcopy(dict(server.data))
    payload.update(overrides or {})
    module = _load_server_module(server)

    internal_ip = normalize_hosted_ip(payload.get("bindaddress"))
    external_ip = normalize_hosted_ip(
        next(
            (payload.get(key) for key in EXTERNAL_IP_KEYS if payload.get(key)),
            internal_ip,
        ),
        default=internal_ip,
    )
    payload["internal_ip"] = internal_ip
    payload["external_ip"] = external_ip

    endpoints = []
    shift_group_keys = []

    for key, value in payload.items():
        if key in ("internal_ip", "external_ip"):
            continue
        if not is_port_key(key):
            continue
        port = _normalize_port_value(value)
        if port is None:
            continue
        key_name = str(key)
        shift_group_keys.append(key_name)
        _add_endpoint(
            endpoints,
            PortEndpoint("internal", internal_ip, port, key_name),
        )
        _add_endpoint(
            endpoints,
            PortEndpoint("external", external_ip, port, key_name),
        )

    for endpoint in _runtime_port_endpoints(
        server,
        module,
        payload,
        allow_stale_saved_ports=overrides is None,
    ):
        if not _endpoint_is_covered(endpoints, endpoint):
            _add_endpoint(endpoints, endpoint)

    temp_server = SimpleNamespace(
        name=getattr(server, "name", "<unknown>"),
        data=payload,
        module=module,
    )
    for hook_name in ("get_query_address", "get_info_address"):
        for endpoint in _hook_endpoint(temp_server, module, hook_name, payload, endpoints):
            _add_endpoint(endpoints, endpoint)

    return PortClaimSet(
        getattr(server, "name", "<unknown>"),
        tuple(endpoints),
        tuple(dict.fromkeys(shift_group_keys)),
    )


def iter_managed_servers(server):
    """Yield other AlphaGSM servers from the datastore directory."""

    datapath = _managed_server_datapath()
    if not datapath or not os.path.isdir(datapath):
        return

    for filename in sorted(os.listdir(datapath)):
        if not filename.endswith(".json"):
            continue
        other_name = filename[:-5]
        if other_name == getattr(server, "name", None):
            continue
        path = os.path.join(datapath, filename)
        try:
            store = data_module.JSONDataStore(path)
        except Exception:
            continue
        module = _load_server_module(SimpleNamespace(data=store, module=None))
        yield SimpleNamespace(name=other_name, data=store, module=module)


def _managed_server_datapath():
    """Return the live AlphaGSM datastore path, honoring server module overrides."""

    server_module = sys.modules.get("server.server")
    if server_module is not None:
        return getattr(server_module, "DATAPATH", DATAPATH)
    return DATAPATH


def probe_live_listener(ip, port):
    """Return ``True`` if a TCP or UDP bind cannot claim *ip*:*port*."""

    host = normalize_hosted_ip(ip)
    for socktype in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        try:
            infos = socket.getaddrinfo(
                host,
                port,
                socket.AF_UNSPEC,
                socktype,
                0,
                socket.AI_PASSIVE,
            )
        except socket.gaierror:
            infos = [(socket.AF_INET, socktype, 0, "", (host, port))]
        for family, stype, proto, _canon, sockaddr in infos:
            sock = socket.socket(family, stype, proto)
            try:
                sock.bind(sockaddr)
            except OSError as exc:
                if getattr(exc, "errno", None) == errno.EADDRNOTAVAIL:
                    return False
                return True
            finally:
                sock.close()
    return False


def _endpoint_conflicts(left, right):
    return (
        left.scope == right.scope
        and left.port == right.port
        and _scope_ips_overlap(left.scope, left.ip, right.ip)
    )


def detect_conflicts(server, overrides=None, include_live=True):
    """Return a list of conflicts for *server* with optional *overrides*."""

    claim_set = collect_claim_set(server, overrides=overrides)
    conflicts = []

    for index, endpoint in enumerate(claim_set.endpoints):
        for other in claim_set.endpoints[index + 1 :]:
            if not _endpoint_conflicts(endpoint, other):
                continue
            conflicts.append(
                PortConflict(
                    "self",
                    endpoint,
                    (
                        f"{endpoint.source_key} and {other.source_key} both claim "
                        f"{endpoint.ip}:{endpoint.port}"
                    ),
                )
            )

    seen_managed = set()
    for managed_server in iter_managed_servers(server):
        other_claims = collect_claim_set(managed_server)
        for endpoint in claim_set.endpoints:
            for other in other_claims.endpoints:
                if not _endpoint_conflicts(endpoint, other):
                    continue
                conflict_id = (
                    managed_server.name,
                    endpoint.ip,
                    endpoint.port,
                    endpoint.source_key,
                    other.source_key,
                )
                if conflict_id in seen_managed:
                    continue
                seen_managed.add(conflict_id)
                conflicts.append(
                    PortConflict(
                        "managed",
                        endpoint,
                        (
                            f"{endpoint.source_key} conflicts with "
                            f"{managed_server.name}:{other.source_key} on "
                            f"{endpoint.ip}:{endpoint.port}"
                        ),
                        managed_server=managed_server.name,
                    )
                )

    if include_live:
        seen_live = set()
        for endpoint in claim_set.endpoints:
            live_id = (endpoint.ip, endpoint.port)
            if live_id in seen_live:
                continue
            seen_live.add(live_id)
            if not probe_live_listener(endpoint.ip, endpoint.port):
                continue
            conflicts.append(
                PortConflict(
                    "unmanaged",
                    endpoint,
                    f"Live listener already holds {endpoint.ip}:{endpoint.port}",
                )
            )

    return conflicts


def recommend_shift(server, max_offset=100, base_overrides=None):
    """Return the first whole-group offset that avoids all detected conflicts."""

    claim_set = collect_claim_set(server, overrides=base_overrides)
    if not claim_set.shift_group_keys:
        return None

    offsets = []
    for offset in range(1, max_offset + 1):
        offsets.extend((offset, -offset))

    base_values = dict(server.data)
    if base_overrides:
        base_values.update(base_overrides)

    for offset in offsets:
        candidate = {}
        valid = True
        for key in claim_set.shift_group_keys:
            current = _normalize_port_value(base_values.get(key))
            if current is None:
                valid = False
                break
            shifted = current + offset
            if shifted <= 0 or shifted > 65535:
                valid = False
                break
            candidate[key] = shifted
        if not valid:
            continue
        if not detect_conflicts(
            server, overrides=candidate, include_live=True
        ):
            return PortShiftRecommendation(offset=offset, values=candidate)

    return None


def describe_conflicts(conflicts):
    """Format conflicts into a compact user-facing diagnostic string."""

    conflicts = list(conflicts)
    if not conflicts:
        return "No port conflicts detected."

    lines = ["Port conflicts detected:"]
    for conflict in conflicts:
        prefix = conflict.kind
        if conflict.managed_server is not None:
            prefix = f"{prefix}:{conflict.managed_server}"
        lines.append(f"- {prefix}: {conflict.message}")
    return "\n".join(lines)
