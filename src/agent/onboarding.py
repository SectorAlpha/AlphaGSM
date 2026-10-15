"""Preview and approve exact local bindings before provider registration or saves."""

import getpass
import hashlib
import ipaddress
import re
import warnings

from server.public_query import PROFILES
from utils.state_io import state_lock
from .lifecycle import AlphaRuntime
from .config import DEFAULT_ORIGIN, ConfigError, canonical_agent_origin
from .contracts import exact, identifier, integer, validate_metadata
from .choices import next_steps, permissions, require_capabilities
from .inventory import inventory, read_local
from .network import global_ip, suggest_public_host
from .publication_config import local_publication


def enroll(cfg, api_origin, transport):
    api_origin = canonical_agent_origin(api_origin or DEFAULT_ORIGIN)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            code = getpass.getpass("Single-use enrollment code: ").strip()
    except getpass.GetPassWarning:
        raise ConfigError("Enrollment requires a terminal that can hide the enrollment code")
    if not code:
        raise ConfigError("An enrollment code is required")
    response = transport(api_origin).request("POST", "/v1/agent/enroll", payload={"code": code})
    cfg.enroll(api_origin, response)
    print("Enrolled. Reporting and management remain disabled until you enable each locally.")


def host(value):
    """Validate an explicit advertised numerical address or DNS name."""
    if not isinstance(value, str) or not value or len(value) > 253 or "%" in value:
        raise ConfigError("Enter a public host or use --host")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        if not re.fullmatch(r"(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", value):
            raise ConfigError("Enter a public host or use --host")
        if any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-')
               for label in value.split('.')) or '.' not in value:
            raise ConfigError("Enter a public DNS name or numerical address")
        return value
    if not address.is_global or address.is_multicast or address.is_reserved:
        raise ConfigError("Advertised address must be globally routable")
    return str(address)


def endpoint(value, default_host, default_port):
    if value:
        if value.startswith("["):
            address, separator, port = value[1:].partition("]:")
            if not separator:
                raise ConfigError("Use [IPv6]:port for an IPv6 endpoint")
        else:
            address, separator, port = value.rpartition(":")
            if not separator:
                raise ConfigError("Use host:port for the advertised endpoint")
        default_host, default_port = address, int(port)
    integer(default_port, 1, 65535)
    return host(default_host), default_port


def candidate(local, value, options, suggest=suggest_public_host):
    matches = [(key, item) for key, item in value['bindings'].items() if item['tag'] == local['tag']]
    binding_id, previous = matches[0] if matches else (None, None)
    if options.binding_id is not None and binding_id is not None and options.binding_id != binding_id:
        raise ConfigError("Reuse the existing binding ID for this local server")
    binding_id = binding_id or options.binding_id
    approved = previous['metadata'] if previous else {}
    if options.game is not None and options.game != local['game_id']:
        raise ConfigError("Selected game does not match the local server module")
    game = local['game_id']
    address = options.host if options.host is not None else approved.get('host')
    if address is None:
        address = suggest(local)
    port = options.port if options.port is not None else approved.get('port', local['port'])
    if port is None:
        raise ConfigError("No valid configured port; set a local port or use --port")
    label = ("[" + address + "]" if address and ':' in address else address) if address else "<public host>"
    response = input("Confirm public host:port for " + local['tag'] + " [" + label + ":" + str(port) + "]: ").strip()
    address, port = endpoint(response, address, port)
    publication, actions = permissions(game, previous, value, options)
    metadata = {"game_id": game, "host": address, "port": port,
                "name": options.name if options.name is not None else approved.get('name', local['name']),
                "capacity": options.capacity if options.capacity is not None else approved.get('capacity', local['capacity'])}
    epoch = previous['epoch'] if previous else options.epoch
    validate_metadata({'binding_id': binding_id or 'pending', 'binding_epoch': epoch, 'publication': publication,
                       'allowed_actions': actions, 'runtime_state': 'unknown', **metadata})
    return {'tag': local['tag'], 'binding_id': binding_id, 'epoch': epoch, 'actions': actions,
            'publication': publication, 'metadata': metadata, **local_publication(options.public_ip, previous)}


def register(transport, value, tag):
    scope = 'reporting' if value['reporting'] else 'management'
    if not value[scope]:
        raise ConfigError("Enrollment has no registration credential")
    response = transport(value['origin']).request('POST', '/v1/agent/bindings', credential=value[scope],
        payload={'scope': scope, 'binding_ref': hashlib.sha256(tag.encode()).hexdigest()})
    exact(response, ('schema_version', 'binding_id', 'binding_epoch'))
    integer(response['schema_version'], 1, 1)
    identifier(response['binding_id'])
    integer(response['binding_epoch'])
    return response['binding_id'], response['binding_epoch']


def guided(cfg, options, transport):
    value = cfg.load()
    local_publication(options.public_ip)
    require_capabilities(value, options.publish is True, options.actions or [])
    if options.host is not None:
        host(options.host)
    if options.binding_id is not None:
        identifier(options.binding_id)
    if options.origin is not None:
        selected_origin = canonical_agent_origin(options.origin)
        if value['origin'] is not None and selected_origin != value['origin']:
            raise ConfigError("Existing enrollment uses a different origin")
    bulk = options.command == 'setup' or options.target == '*'
    if bulk and options.binding_id is not None:
        raise ConfigError("Select one local tag when supplying a binding ID")
    if bulk:
        locals_, failures = inventory()
    else:
        locals_, failures = [read_local(options.target)], []
    if bulk and options.port is not None and len(locals_) > 1:
        raise ConfigError("Use per-server public endpoint prompts or bind one tag when overriding --port")
    for tag, reason in failures:
        print("Skipped " + tag + ": " + reason)
    if not locals_:
        raise ConfigError("No eligible local servers found")
    if len(locals_) + len(value['bindings']) - sum(
            any(item['tag'] == local['tag'] for item in value['bindings'].values()) for local in locals_) > 100:
        raise ConfigError("At most 100 local bindings are allowed")
    print("Network addresses are suggestions; confirm NAT/public ports. Ownership still requires the central challenge.")
    cached_host = []
    def suggest(local):
        configured = next((global_ip(local[key]) for key in ('publicip', 'externalip', 'hostip')
                           if global_ip(local[key])), None)
        if configured:
            return configured
        if not cached_host:
            cached_host.append(suggest_public_host(local))
        return cached_host[0]
    candidates = []
    for local in locals_:
        print("Local server: " + local['tag'] + " | " + local['name'] + " | " + local['game_id'] +
              " | port=" + str(local['port']) + " | capacity=" + str(local['capacity']))
        existing = any(item['tag'] == local['tag'] for item in value['bindings'].values())
        if bulk and options.port is None and local['port'] is None and not existing:
            failures.append((local['tag'], 'No valid configured port; set a local port or use --port'))
            print("Skipped " + local['tag'] + ": " + failures[-1][1])
            continue
        candidates.append(candidate(local, value, options, suggest))
    if not candidates:
        raise ConfigError("No configured local servers selected")
    for item in candidates:
        metadata = item['metadata']
        print("Preview: " + item['tag'] + " -> " + metadata['host'] + ":" + str(metadata['port']) +
              " | game=" + metadata["game_id"] + " | name=" + metadata["name"] +
              " | capacity=" + str(metadata["capacity"]) + " | publication=" + ('yes' if item['publication'] else 'no') +
              " | actions=" + (','.join(item['actions']) or 'none') +
              " | binding=" + (item['binding_id'] or 'pending provider registration') +
              " | epoch=" + (str(item['epoch']) if item['binding_id'] else 'pending') +
              " | machine IPs=" + (','.join(item.get('expected_public_ips', [])) or 'automatic'))
    if input("Save these exact bindings? [no]: ").strip().lower() not in ('y', 'yes'):
        print("Cancelled. Local bindings are unchanged.")
        return 1
    for item in candidates:
        if read_local(item['tag'])['game_id'] != item['metadata']['game_id']:
            raise ConfigError("Local game changed during preview; run the command again")
    with state_lock(cfg.path):
        unchanged(cfg, value)
        if value['installation_id'] is None:
            enroll(cfg, options.origin, transport)
            value = cfg.load()
    for item in candidates:
        require_capabilities(value, item['publication'], item['actions'])
    failed = save_candidates(cfg, value, candidates, transport) or bool(failures)
    next_steps(value)
    return 1 if failed else 0


def unchanged(cfg, snapshot):
    current = cfg.load()
    fields = ('origin', 'installation_id', 'credential_generation', 'reporting', 'management',
              'reporting_enabled', 'management_enabled', 'policy_version', 'bindings')
    if any(current[key] != snapshot[key] for key in fields):
        raise ConfigError("Local policy changed during preview; run the command again")


def save_candidates(cfg, value, candidates, transport):
    failed = False
    for item in candidates:
        try:
            # Match the lifecycle lock order: exact local target, then agent policy.
            with AlphaRuntime().lock(item['tag']), state_lock(cfg.path):
                unchanged(cfg, value)
                if read_local(item['tag'])['game_id'] != item['metadata']['game_id']:
                    raise ConfigError("Local game changed after preview")
                binding_id, epoch = item['binding_id'], item['epoch']
                if binding_id is None:
                    binding_id, epoch = register(transport, value, item['tag'])
                previous = value['bindings'].get(binding_id)
                if previous is not None and previous['tag'] != item['tag']:
                    raise ConfigError('Provider binding ID is already assigned to another local server')
                planned = {'tag': item['tag'], 'epoch': epoch, 'actions': item['actions'],
                           'publication': item['publication'], 'metadata': item['metadata'],
                           **local_publication(item.get('expected_public_ips'), previous)}
                if previous != planned:
                    cfg.bind(binding_id, item['tag'], epoch, actions=item['actions'], publication=item['publication'],
                             metadata=item['metadata'], **local_publication(item.get('expected_public_ips'), previous))
                value = cfg.load()
            print("Bound " + item['tag'] + " (" + binding_id + ").")
        except (OSError, ValueError, RuntimeError):
            failed = True
            print("Failed " + item['tag'] + ": provider registration, local policy or local game changed; retry safely.")
    return failed
