"""Withhold public hostnames whose complete DNS answers do not match this machine."""

from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeout
from server.public_query import PROFILES
import ipaddress
import time

from .dns_lookup import DNS_TIMEOUT, MAX_DNS_ADDRESSES, PreflightError, resolve_host
from .inventory import read_local
from .network import suggest_public_host
from .publication_config import normalize_public_ips, public_ip

BATCH_TIMEOUT = 30.0
DNS_WORKERS = 8


def numerical(host):
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def expected_addresses(binding, cache, *, read, discover):
    if 'expected_public_ips' in binding:
        return set(normalize_public_ips(binding['expected_public_ips']))
    try:
        local = read(binding['tag'])
    except (OSError, ValueError, RuntimeError):
        local = {}
    selected = {public_ip(local.get(key)) for key in ('publicip', 'externalip', 'hostip')} - {None}
    if selected:
        return selected
    if not cache:
        cache.append(public_ip(discover({})))
    if cache[0] is None:
        raise PreflightError("Public machine IP unavailable; retry or bind with --public-ip for NAT/multiple IPs")
    return {cache[0]}


def matched_addresses(answers, expected):
    if not isinstance(answers, (list, tuple, set, frozenset)) or not 1 <= len(answers) <= MAX_DNS_ADDRESSES:
        raise PreflightError("DNS returned no usable complete address set; check A and AAAA records")
    selected = {public_ip(address) for address in answers}
    if None in selected:
        raise PreflightError("DNS includes a non-global address; only public A and AAAA addresses are allowed")
    if not selected <= expected:
        raise PreflightError("DNS does not match this machine; fix A/AAAA records or set --public-ip for its public IPs")
    return sorted(selected)


def current_binding(item, value):
    binding = value['bindings'].get(item['binding_id'])
    if (not value['reporting_enabled'] or binding is None or not binding['publication']
            or binding['epoch'] != item['binding_epoch']
            or any(binding['metadata'][key] != item[key] for key in ('game_id', 'host', 'port'))):
        raise PreflightError("Local publication approval or endpoint changed; retry with the next report")
    if item['game_id'] not in PROFILES:
        raise PreflightError("This game has no supported public query profile; private binding remains available")
    return binding


def preflight_report(payload, value, *, resolve=None, discover=None, read=None):
    """Check fresh DNS each renewal, changing only outgoing publication flags."""
    resolve = resolve or resolve_host
    discover = discover or suggest_public_host
    read = read or read_local
    outgoing = {**payload, 'bindings': [dict(item) for item in payload['bindings']]}
    failures, candidates, cache = {}, {}, []
    deadline = time.monotonic() + BATCH_TIMEOUT
    for item in outgoing['bindings']:
        if not item['publication'] or numerical(item['host']):
            continue
        binding_id = item['binding_id']
        try:
            binding = current_binding(item, value)
            expected = expected_addresses(binding, cache, read=read, discover=discover)
            candidates[binding_id] = (item, expected)
        except PreflightError as exc:
            item['publication'] = False
            failures[binding_id] = str(exc)
        except (OSError, ValueError, RuntimeError):
            item['publication'] = False
            failures[binding_id] = 'Public machine IP unavailable or invalid; use --public-ip with its global IPs'
    hosts = sorted({item['host'] for item, expected in candidates.values()})
    offset = ((payload['sequence'] - 1) * DNS_WORKERS) % max(1, len(hosts))
    hosts = hosts[offset:] + hosts[:offset]
    answers = {}

    def fresh(host):
        remaining = min(DNS_TIMEOUT, deadline - time.monotonic())
        if remaining <= 0:
            raise PreflightError("DNS batch budget exceeded; retry publication")
        return resolve(host, remaining)

    if hosts:
        # dnspython lifetimes bound running tasks, so executor shutdown cannot
        # retain system getaddrinfo calls or accumulate uncancellable workers.
        with ThreadPoolExecutor(max_workers=DNS_WORKERS, thread_name_prefix='alphagsm-dns') as pool:
            pending = {pool.submit(fresh, host): host for host in hosts}
            try:
                for future in as_completed(pending, timeout=max(0, deadline - time.monotonic())):
                    host = pending[future]
                    try:
                        answers[host] = future.result()
                    except (OSError, ValueError, RuntimeError):
                        answers[host] = None
            except FutureTimeout:
                for future in pending:
                    future.cancel()
    for binding_id, (item, expected) in candidates.items():
        try:
            addresses = matched_addresses(answers.get(item['host']), expected)
            if PROFILES.get(item['game_id']) == 'a2s' and any(
                    ipaddress.ip_address(address).version != 4 for address in addresses):
                raise PreflightError('The A2S public profile supports IPv4 only; check the hostname AAAA record')
        except (OSError, ValueError, RuntimeError) as exc:
            item['publication'] = False
            failures[binding_id] = str(exc)
    return outgoing, failures


def final_report(payload, checked, current):
    """No network: withdraw stale approvals immediately before the locked POST."""
    outgoing = {**payload, 'bindings': [dict(item) for item in payload['bindings']]}
    failures = {}
    for item in outgoing['bindings']:
        if not item['publication']:
            continue
        binding_id = item['binding_id']
        try:
            binding = current_binding(item, current)
            previous = checked['bindings'].get(binding_id)
            if previous is None or binding.get('expected_public_ips') != previous.get('expected_public_ips'):
                raise PreflightError("Expected machine IPs changed during DNS validation; retry publication")
        except (OSError, ValueError, RuntimeError) as exc:
            item['publication'] = False
            failures[binding_id] = str(exc)
    return outgoing, failures
