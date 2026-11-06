"""Hostname publication stays local until every fresh DNS address matches this machine."""
from contextlib import nullcontext
import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent import cli
from agent.config import Config
from agent.reporting import report_snapshot
from agent.service import Service
from test_onboarding import answers, enrolled, local_servers, provider


def preflight():
    assert importlib.util.find_spec('agent.preflight'), 'missing hostname publication preflight'
    return importlib.import_module('agent.preflight')


def add_binding(cfg, binding_id='world', host='game.example', expected=None, publication=True):
    kwargs = {} if expected is None else {'expected_public_ips': expected}
    cfg.bind(binding_id, binding_id, 1, actions=[], publication=publication,
             metadata=dict(game_id='minecraft.vanilla', host=host, port=25565, name='World', capacity=20), **kwargs)


def runtime():
    return SimpleNamespace(lock=lambda tag: nullcontext(), state=lambda tag: 'running', metadata=lambda tag, approved: approved)


def published_config(tmp_path):
    cfg = enrolled(tmp_path)
    cfg.enable(reporting=True)
    return cfg


def test_runtime_pins_bounded_dns_library():
    root = Path(__file__).resolve().parents[3]
    assert 'dnspython==2.7.0' in (root / 'requirements-runtime.txt').read_text().splitlines()


def test_local_expected_ips_are_validated_optional_and_preserved_on_rerun(tmp_path):
    cfg = enrolled(tmp_path)
    add_binding(cfg, expected=['2606:4700:4700:0:0:0:0:1111', '8.8.8.8', '8.8.8.8'])
    value = cfg.load()
    assert value['bindings']['world']['expected_public_ips'] == ['2606:4700:4700::1111', '8.8.8.8']
    add_binding(cfg)
    assert cfg.load() == value
    for invalid in (['10.1.2.3'], ['127.0.0.1'], ['game.example'], [], '8.8.8.8', ['224.0.0.1']):
        with pytest.raises(ValueError):
            add_binding(cfg, expected=invalid)
        assert cfg.load() == value


def test_old_config_and_numeric_private_reports_remain_offline(tmp_path, monkeypatch):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, 'numeric', host='8.8.8.8')
    add_binding(cfg, 'private', publication=False)
    snapshot = report_snapshot(cfg, runtime())
    def forbidden(*args, **kwargs):
        pytest.fail('private/numeric reports must not discover, resolve or probe')
    outgoing, failures = module.preflight_report(snapshot, cfg.load(), resolve=forbidden, discover=forbidden, read=forbidden)
    assert outgoing == snapshot and not failures
    assert 'expected_public_ips' not in json.dumps(outgoing)


@pytest.mark.parametrize('dns_answers, expected, allowed', [
    (['8.8.8.8'], ['8.8.8.8'], True),
    (['8.8.4.4'], ['8.8.8.8'], False),
    ([], ['8.8.8.8'], False),
    (['8.8.8.8', '10.1.2.3'], ['8.8.8.8'], False),
    (['8.8.8.8', '8.8.4.4'], ['8.8.8.8'], False),
    (['8.8.8.8', '2606:4700:4700::1111'], ['8.8.8.8', '2606:4700:4700::1111'], True),
    (['8.8.8.8', '2606:4700:4700::1111'], ['8.8.8.8'], False),
])
def test_every_dns_answer_must_be_global_and_match_expected_machine(tmp_path, dns_answers, expected, allowed):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=expected)
    snapshot = report_snapshot(cfg, runtime())
    old = cfg.path.read_bytes()
    calls = []
    def resolve(host, timeout):
        calls.append((host, timeout))
        return dns_answers
    outgoing, failures = module.preflight_report(snapshot, cfg.load(), resolve=resolve)
    assert outgoing['bindings'][0]['publication'] is allowed
    assert bool(failures) is not allowed
    assert snapshot['bindings'][0]['publication'] is True and cfg.path.read_bytes() == old
    assert calls[0][0] == 'game.example' and 0 < calls[0][1] <= 2
    assert 'expected_public_ips' not in json.dumps(outgoing)


def test_dns_change_and_repair_are_checked_every_renewal_without_consent_changes(tmp_path):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    replies = iter([['8.8.8.8'], ['8.8.4.4'], ['8.8.8.8']])
    flags = []
    for _ in range(3):
        snapshot = report_snapshot(cfg, runtime())
        outgoing, _ = module.preflight_report(snapshot, cfg.load(), resolve=lambda host, timeout: next(replies))
        flags.append(outgoing['bindings'][0]['publication'])
    assert flags == [True, False, True]
    assert cfg.load()['bindings']['world']['publication'] is True


def test_one_bad_hostname_does_not_withdraw_other_bindings(tmp_path):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, 'bad', host='bad.example', expected=['8.8.8.8'])
    add_binding(cfg, 'good', host='good.example', expected=['8.8.8.8'])
    add_binding(cfg, 'numeric', host='8.8.8.8')
    snapshot = report_snapshot(cfg, runtime())
    def resolve(host, timeout):
        if host == 'bad.example':
            raise TimeoutError('resolver unavailable')
        return ['8.8.8.8']
    outgoing, failures = module.preflight_report(snapshot, cfg.load(), resolve=resolve)
    assert {item['binding_id']: item['publication'] for item in outgoing['bindings']} == {'bad': False, 'good': True, 'numeric': True}
    assert set(failures) == {'bad'}


def test_machine_ip_discovery_is_once_per_batch_and_local_hints_take_priority(tmp_path):
    module = preflight()
    cfg = published_config(tmp_path)
    for name in ('a', 'b', 'hint'):
        add_binding(cfg, name, host=name + '.example')
    calls = []
    def read(tag):
        return {'publicip': '8.8.4.4' if tag == 'hint' else '10.0.0.1'}
    def discover(metadata):
        calls.append(metadata)
        return '8.8.8.8'
    outgoing, failures = module.preflight_report(report_snapshot(cfg, runtime()), cfg.load(), read=read, discover=discover,
        resolve=lambda host, timeout: ['8.8.4.4' if host == 'hint.example' else '8.8.8.8'])
    assert all(item['publication'] for item in outgoing['bindings']) and not failures
    assert len(calls) == 1


def test_unavailable_machine_ip_withholds_hostname_with_actionable_reason(tmp_path):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg)
    outgoing, failures = module.preflight_report(report_snapshot(cfg, runtime()), cfg.load(), read=lambda tag: {},
        discover=lambda metadata: None, resolve=lambda *args: pytest.fail('no expected machine IP means no DNS/probe'))
    assert not outgoing['bindings'][0]['publication']
    assert '--public-ip' in failures['world']


def test_service_gates_actual_post_without_changing_local_consent(tmp_path, monkeypatch):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    monkeypatch.setattr(module, 'resolve_host', lambda host, timeout: ['8.8.4.4'])
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(request=lambda method, path, **kwargs: sent.append(kwargs['payload'])))
    service.report_once()
    assert sent[0]['bindings'][0]['publication'] is False
    assert cfg.load()['bindings']['world']['publication'] is True
    assert 'expected_public_ips' not in json.dumps(sent)


def test_guided_override_is_local_only_and_survives_exact_rerun(tmp_path, local_servers, provider, monkeypatch, capsys):
    cfg = enrolled(tmp_path)
    args = ['bind', 'world', '--host', 'game.example', '--public-ip', '8.8.8.8', '--public-ip', '2606:4700:4700::1111']
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(args, root=cfg.root) == 0
    old = cfg.path.read_bytes()
    binding = next(iter(cfg.load()['bindings'].values()))
    assert binding['expected_public_ips'] == ['2606:4700:4700::1111', '8.8.8.8']
    assert '8.8.8.8' in capsys.readouterr().out
    assert set(provider[0][3]['payload']) == {'scope', 'binding_ref'}
    answers(monkeypatch, ['', '', '', 'y'])
    assert cli.run(['bind', 'world', '--host', 'game.example'], root=cfg.root) == 0
    assert cfg.path.read_bytes() == old and len(provider) == 1


@pytest.mark.parametrize('address', ['2002:0808:0808::1', '::ffff:8.8.8.8', '2001:0:4136:e378:8000:63bf:3fff:fdd2'])
def test_expected_ip_and_dns_answers_reject_ipv6_translation_tunnels(address):
    from agent.publication_config import normalize_public_ips
    module = preflight()
    with pytest.raises(ValueError):
        normalize_public_ips([address])
    with pytest.raises(ValueError):
        module.matched_addresses([address], {address})


def test_explicit_endpoint_probe_uses_only_matched_pinned_ips_and_original_host(tmp_path):
    module = preflight()
    endpoint = importlib.import_module('agent.endpoint_check') if importlib.util.find_spec('agent.endpoint_check') else None
    assert endpoint, 'missing explicit endpoint check'
    cfg = enrolled(tmp_path)
    add_binding(cfg, expected=['8.8.8.8', '2606:4700:4700::1111'])
    binding = cfg.load()['bindings']['world']
    calls = []
    result = endpoint.check_endpoint(binding, resolve=lambda host, timeout: ['8.8.8.8', '2606:4700:4700::1111'],
        probe=lambda game, address, port, **kwargs: calls.append((game, address, port, kwargs)) or {})
    assert result == ['2606:4700:4700::1111', '8.8.8.8']
    assert {call[1] for call in calls} == {'8.8.8.8', '2606:4700:4700::1111'}
    assert all(call[3]['virtual_host'] == 'game.example' and 0 < call[3]['timeout'] <= 5 for call in calls)
    assert cfg.load()['bindings']['world'] == binding


def test_explicit_endpoint_check_rejects_unmatched_or_timeout_dns_without_probe(tmp_path):
    assert importlib.util.find_spec('agent.endpoint_check'), 'missing explicit endpoint check'
    endpoint = importlib.import_module('agent.endpoint_check')
    cfg = enrolled(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    def no_probe(*args, **kwargs):
        pytest.fail('unmatched/failed DNS cannot trigger native I/O')
    with pytest.raises(ValueError):
        endpoint.check_endpoint(cfg.load()['bindings']['world'], resolve=lambda host, timeout: ['10.1.2.3'], probe=no_probe)
    def unavailable(host, timeout):
        raise TimeoutError('DNS expired')
    with pytest.raises(ValueError):
        endpoint.check_endpoint(cfg.load()['bindings']['world'], resolve=unavailable, probe=no_probe)


def test_native_failure_explains_public_port_and_nat_loopback(tmp_path):
    assert importlib.util.find_spec('agent.endpoint_check'), 'missing explicit endpoint check'
    endpoint = importlib.import_module('agent.endpoint_check')
    cfg = enrolled(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    def refused(*args, **kwargs):
        raise OSError('refused')
    with pytest.raises(ValueError, match='NAT loopback'):
        endpoint.check_endpoint(cfg.load()['bindings']['world'], resolve=lambda host, timeout: ['8.8.8.8'], probe=refused)


def test_check_endpoint_cli_does_not_write_config_or_offer_publication(tmp_path, local_servers, monkeypatch, capsys):
    assert importlib.util.find_spec('agent.endpoint_check'), 'missing explicit endpoint check'
    endpoint = importlib.import_module('agent.endpoint_check')
    cfg = enrolled(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'], publication=False)
    old = cfg.path.read_bytes()
    monkeypatch.setattr(endpoint, 'check_endpoint', lambda binding, expected_public_ips=None: ['8.8.8.8'])
    assert cli.run(['check-endpoint', 'world'], root=cfg.root) == 0
    assert cfg.path.read_bytes() == old
    assert 'ownership challenge' in capsys.readouterr().out


def test_a2s_hostname_with_ipv6_answer_is_withheld_with_profile_reason(tmp_path):
    module = preflight()
    cfg = published_config(tmp_path)
    cfg.bind('tf2', 'tf2', 1, actions=[], publication=True, expected_public_ips=['2606:4700:4700::1111'],
             metadata=dict(game_id='teamfortress2', host='tf2.example', port=27015, name='TF2', capacity=24))
    outgoing, failures = module.preflight_report(report_snapshot(cfg, runtime()), cfg.load(),
        resolve=lambda host, timeout: ['2606:4700:4700::1111'])
    assert outgoing['bindings'][0]['publication'] is False
    assert 'IPv4 only' in failures['tf2']


def test_repeated_small_batches_do_not_permanently_starve_a_healthy_last_hostname(tmp_path, monkeypatch):
    import time
    module = preflight()
    cfg = published_config(tmp_path)
    hosts = ['host-' + str(index) + '.example' for index in range(7)]
    last = list(set(hosts))[-1]
    for index, host in enumerate(hosts):
        add_binding(cfg, str(index), host=host, expected=['8.8.8.8'])
    monkeypatch.setattr(module, 'DNS_WORKERS', 1)
    monkeypatch.setattr(module, 'DNS_TIMEOUT', .04)
    monkeypatch.setattr(module, 'BATCH_TIMEOUT', .05)
    def resolve(host, timeout):
        if host == last:
            return ['8.8.8.8']
        time.sleep(timeout)
        raise TimeoutError('DNS expired')
    checked = []
    for _ in hosts:
        outgoing, _ = module.preflight_report(report_snapshot(cfg, runtime()), cfg.load(), resolve=resolve)
        checked += [item['publication'] for item in outgoing['bindings'] if item['host'] == last]
    assert any(checked), 'Repeated early DNS failures permanently starved the last healthy hostname'


def test_invalid_expected_override_rejects_before_guidance_or_discovery(tmp_path, local_servers, provider, monkeypatch):
    cfg = enrolled(tmp_path)
    monkeypatch.setattr('builtins.input', lambda prompt: pytest.fail('invalid --public-ip must reject before prompts'))
    assert cli.run(['bind', 'world', '--host', 'game.example', '--public-ip', '10.0.0.1'], root=cfg.root) == 1
    assert not cfg.load()['bindings'] and not provider


def test_explicit_native_check_uses_real_bounded_slp_with_original_virtual_host(monkeypatch):
    """Loopback is permitted only by this test's explicit address-policy stub."""
    import socket
    import threading
    from agent import endpoint_check, publication_config
    module = preflight()
    try:
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
    except PermissionError:
        pytest.skip('The native protocol regression needs loopback socket permission')
    listener.listen(1)
    listener.settimeout(2)
    port = listener.getsockname()[1]
    seen, errors = [], []
    def peer():
        try:
            connection, _ = listener.accept()
            with connection:
                connection.settimeout(2)
                length = connection.recv(1)[0]
                handshake = bytearray()
                while len(handshake) < length:
                    handshake.extend(connection.recv(length - len(handshake)))
                seen.append(bytes(handshake))
                assert connection.recv(2) == b'\x01\x00'
                status = b'{"description":"World","players":{"online":0,"max":20},"version":{"name":"test"}}'
                assert len(status) < 126
                connection.sendall(bytes([len(status) + 2, 0, len(status)]) + status)
        except Exception as exc:
            errors.append(exc)
    worker = threading.Thread(target=peer, daemon=True)
    worker.start()
    original = publication_config.public_ip
    allowed_test_address = lambda value: '127.0.0.1' if value == '127.0.0.1' else original(value)
    monkeypatch.setattr(publication_config, 'public_ip', allowed_test_address)
    monkeypatch.setattr(module, 'public_ip', allowed_test_address)
    binding = {'tag': 'world', 'expected_public_ips': ['127.0.0.1'],
               'metadata': {'game_id': 'minecraft.vanilla', 'host': 'game.example', 'port': port}}
    try:
        assert endpoint_check.check_endpoint(binding, resolve=lambda host, timeout: ['127.0.0.1']) == ['127.0.0.1']
        worker.join(2)
        assert not worker.is_alive() and not errors
        assert b'game.example' in seen[0] and b'127.0.0.1' not in seen[0]
    finally:
        listener.close()
        worker.join(2)


@pytest.mark.parametrize('change', ['removed', 'private', 'host_changed'])
def test_local_hostname_binding_changes_withhold_stale_snapshot_before_dns(tmp_path, change):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    snapshot = report_snapshot(cfg, runtime())
    if change == 'removed':
        cfg.unbind('world')
    elif change == 'private':
        cfg.publication('world', False)
    else:
        add_binding(cfg, host='replacement.example')
    outgoing, failures = module.preflight_report(snapshot, cfg.load(),
        resolve=lambda *args: pytest.fail('changed local binding must not resolve old hostname'))
    assert outgoing['bindings'][0]['publication'] is False and failures


def test_hostname_preflight_pool_is_bounded_and_does_not_leave_workers(tmp_path):
    import threading
    import time
    module = preflight()
    cfg = published_config(tmp_path)
    for index in range(20):
        add_binding(cfg, str(index), host='host-' + str(index) + '.example', expected=['8.8.8.8'])
    lock = threading.Lock()
    active = 0
    peak = 0
    def resolve(host, timeout):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            time.sleep(.005)
            return ['8.8.8.8']
        finally:
            with lock:
                active -= 1
    for _ in range(2):
        outgoing, failures = module.preflight_report(report_snapshot(cfg, runtime()), cfg.load(), resolve=resolve)
        assert all(item['publication'] for item in outgoing['bindings']) and not failures
    assert peak <= module.DNS_WORKERS and active == 0
    assert not any(worker.name.startswith('alphagsm-dns') for worker in threading.enumerate())


@pytest.mark.parametrize('change', ['publication', 'reporting', 'endpoint', 'expected_ip'])
def test_service_rechecks_policy_after_dns_before_actual_post(tmp_path, monkeypatch, change):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    def resolve(host, timeout):
        if change == 'publication':
            cfg.publication('world', False)
        elif change == 'reporting':
            cfg.enable(reporting=False)
        elif change == 'endpoint':
            add_binding(cfg, host='changed.example')
        else:
            add_binding(cfg, expected=['8.8.4.4'])
        return ['8.8.8.8']
    monkeypatch.setattr(module, 'resolve_host', resolve)
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(
        request=lambda method, path, **kwargs: sent.append(kwargs)))
    service.report_once()
    assert len(sent) == 1 and sent[0]['payload']['bindings'][0]['publication'] is False


def test_service_uses_current_reporting_credential_after_dns_rotation(tmp_path, monkeypatch):
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    def resolve(host, timeout):
        cfg.replace_credential('reporting', 'rotated-key', 'n' * 43)
        return ['8.8.8.8']
    monkeypatch.setattr(module, 'resolve_host', resolve)
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(request=lambda method, path, **kwargs: sent.append(kwargs)))
    service.report_once()
    assert sent[0]['credential'] == {'key_id': 'rotated-key', 'secret': 'n' * 43}
    assert sent[0]['payload']['bindings'][0]['publication'] is True


def test_final_post_is_serialized_with_operator_policy_mutations(tmp_path, monkeypatch):
    import threading
    module = preflight()
    cfg = published_config(tmp_path)
    add_binding(cfg, expected=['8.8.8.8'])
    monkeypatch.setattr(module, 'resolve_host', lambda host, timeout: ['8.8.8.8'])
    attempted, changed = threading.Event(), threading.Event()
    def revoke():
        attempted.set()
        cfg.publication('world', False)
        changed.set()
    worker = threading.Thread(target=revoke)
    def post(method, path, **kwargs):
        worker.start()
        assert attempted.wait(1)
        assert not changed.wait(.05), 'Policy mutation was not serialized with the final POST'
        assert kwargs['payload']['bindings'][0]['publication'] is True
        return {'accepted': True}
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(request=post))
    try:
        service.report_once()
    finally:
        worker.join(2)
    assert changed.is_set() and cfg.load()['bindings']['world']['publication'] is False


def test_service_never_sends_new_relationship_credentials_through_old_transport(tmp_path):
    cfg = published_config(tmp_path)
    add_binding(cfg, host='8.8.8.8')
    sent = []
    service = Service(cfg, runtime=runtime(), transport=SimpleNamespace(request=lambda *args, **kwargs: sent.append(kwargs) or {}))
    cfg.enable(reporting=False)
    cfg.forget()
    cfg.enroll('https://replacement.example', dict(schema_version=1, installation_id='new-install', credential_generation=1,
        reporting=dict(key_id='new-report', secret='n' * 43), management=dict(key_id='new-management', secret='m' * 43)))
    add_binding(cfg, host='8.8.8.8')
    cfg.enable(reporting=True, management=True)
    assert service.report_once() is None
    assert service.management_once() is None
    assert sent == []
