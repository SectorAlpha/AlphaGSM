"""Only allowlisted local metadata and globally routable network suggestions."""
import importlib
import json
from types import SimpleNamespace
import ssl
import urllib.request

import pytest


def module(name):
    assert importlib.util.find_spec('agent.' + name), 'missing focused discovery helper'
    return importlib.import_module('agent.' + name)


def test_inventory_excludes_secrets_links_invalid_and_cross_user(tmp_path, monkeypatch):
    inventory = module('inventory')
    import server.server as server_module
    monkeypatch.setattr(server_module, 'DATAPATH', str(tmp_path))
    (tmp_path / 'world.json').write_text(json.dumps(dict(module='minecraft.vanilla', port=25565,
        servername='World', maxplayers=20, rconpassword='NEVER-COPY')))
    (tmp_path / 'world.secrets.json').write_text('{"secret":"NEVER-READ"}')
    (tmp_path / 'bad tag.json').write_text('{}')
    (tmp_path / 'link.json').symlink_to(tmp_path / 'world.json')
    (tmp_path / 'other.json').write_text('{}')
    actual_stat = inventory.os.fstat
    monkeypatch.setattr(inventory.os, 'fstat', lambda fd: SimpleNamespace(**{
        key: (99999 if key == 'st_uid' else getattr(actual_stat(fd), key))
        for key in ('st_uid', 'st_mode', 'st_size')}) if inventory.os.readlink('/proc/self/fd/' + str(fd)).endswith('other.json') else actual_stat(fd))
    items, failures = inventory.inventory()
    assert [item['tag'] for item in items] == ['world']
    assert 'NEVER' not in repr((items, failures))
    assert set(items[0]) == {'tag', 'game_id', 'name', 'port', 'capacity', 'publicip', 'externalip', 'hostip'}
    assert all('secrets' not in tag for tag, reason in failures)


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '0.0.0.0', '169.254.1.1', '224.0.0.1', '::1', 'example.com'])
def test_global_ip_rejects_non_global_and_hostnames(address):
    assert module('network').global_ip(address) is None


def test_suggestion_prefers_configured_public_numeric_without_network(monkeypatch):
    network = module('network')
    monkeypatch.setattr(network, 'routing_ip', lambda: pytest.fail('routing should not be called'))
    monkeypatch.setattr(network, 'lookup_ip', lambda: pytest.fail('lookup should not be called'))
    assert network.suggest_public_host({'publicip': '10.0.0.1', 'externalip': '8.8.8.8'}) == '8.8.8.8'


def test_suggestion_uses_routing_global_then_lookup(monkeypatch):
    network = module('network')
    monkeypatch.setattr(network, 'routing_ip', lambda: '8.8.4.4')
    monkeypatch.setattr(network, 'lookup_ip', lambda: pytest.fail('lookup should not be called'))
    assert network.suggest_public_host({}) == '8.8.4.4'
    monkeypatch.setattr(network, 'routing_ip', lambda: '192.168.1.2')
    monkeypatch.setattr(network, 'lookup_ip', lambda: '1.1.1.1')
    assert network.suggest_public_host({}) == '1.1.1.1'


class Response:
    def __init__(self, body=b'8.8.8.8', url='https://api.ipify.org'):
        self.body = body
        self.url = url
        self.fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=lambda value: None)))
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def geturl(self):
        return self.url
    def read1(self, limit):
        body, self.body = self.body[:limit], self.body[limit:]
        return body


def lookup(monkeypatch, response):
    network = module('network')
    captured = []
    def opener(*handlers):
        captured.extend(handlers)
        def open_request(request, timeout):
            assert request.full_url == 'https://api.ipify.org'
            assert request.get_method() == 'GET'
            assert request.data is None
            assert not any(key.lower() in ('authorization', 'cookie') for key in request.headers)
            assert 0 < timeout <= 5
            return response
        return SimpleNamespace(open=open_request)
    monkeypatch.setattr(network.urllib.request, 'build_opener', opener)
    return network.lookup_ip(), captured


def test_lookup_uses_verified_tls_no_proxy_and_no_redirect_or_secrets(monkeypatch):
    value, handlers = lookup(monkeypatch, Response())
    assert value == '8.8.8.8'
    assert next(h for h in handlers if isinstance(h, urllib.request.ProxyHandler)).proxies == {}
    tls = next(h for h in handlers if isinstance(h, urllib.request.HTTPSHandler))._context
    assert tls.verify_mode == ssl.CERT_REQUIRED and tls.check_hostname
    redirect = next(h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
    with pytest.raises(OSError):
        redirect.redirect_request(None, None, 302, '', {}, 'https://elsewhere.example')


@pytest.mark.parametrize('response', [Response(b'10.1.2.3'), Response(b'x' * 100), Response(url='https://elsewhere.example')])
def test_lookup_fails_closed_for_non_global_oversized_or_changed_url(monkeypatch, response):
    assert lookup(monkeypatch, response)[0] is None


def test_lookup_failure_offline_is_graceful(monkeypatch):
    network = module('network')
    def unavailable(*args, **kwargs):
        raise ssl.SSLCertVerificationError('hostile certificate')
    monkeypatch.setattr(network.urllib.request, 'build_opener', lambda *args: SimpleNamespace(open=unavailable))
    assert network.lookup_ip() is None


def test_lookup_total_time_budget_is_bounded(monkeypatch):
    network = module('network')
    moments = iter([0, 6])
    monkeypatch.setattr(network.time, 'monotonic', lambda: next(moments, 6))
    assert lookup(monkeypatch, Response())[0] is None


def test_lookup_rejects_ipv6_response_from_ipv4_service(monkeypatch):
    assert lookup(monkeypatch, Response(b'2606:4700:4700::1111'))[0] is None


def test_routing_socket_does_not_send_and_ignores_local_address(monkeypatch):
    network = module('network')
    class Route:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def settimeout(self, value):
            assert value == 1
        def connect(self, address):
            assert address == ('1.1.1.1', 80)
        def getsockname(self):
            return ('192.168.1.2', 40000)
    monkeypatch.setattr(network.socket, 'socket', lambda *args: Route())
    assert network.routing_ip() is None


def test_inventory_does_not_construct_servers_or_invoke_hooks(tmp_path, monkeypatch):
    inventory = module('inventory')
    import server.server as server_module
    monkeypatch.setattr(server_module, 'DATAPATH', str(tmp_path))
    monkeypatch.setattr(server_module, 'Server', lambda *args: pytest.fail('constructor can load secrets'))
    (tmp_path / 'world.json').write_text(json.dumps(dict(module='minecraft.vanilla', queryport='invalid', port='25565')))
    items, failures = inventory.inventory()
    assert items[0]['port'] == 25565 and not failures


def test_inventory_limits_to_100_and_reports_remaining_locals(tmp_path, monkeypatch):
    inventory = module('inventory')
    import server.server as server_module
    monkeypatch.setattr(server_module, 'DATAPATH', str(tmp_path))
    for index in range(101):
        (tmp_path / ('server-' + str(index) + '.json')).write_text('{"module":"minecraft.vanilla","port":25565}')
    items, failures = inventory.inventory()
    assert len(items) == 100 and len(failures) == 1
    assert '100' in failures[0][1]


def test_inventory_rejects_oversized_local_file(tmp_path, monkeypatch):
    inventory = module('inventory')
    import server.server as server_module
    monkeypatch.setattr(server_module, 'DATAPATH', str(tmp_path))
    (tmp_path / 'oversized.json').write_bytes(b'x' * (inventory.MAX_DATA_BYTES + 1))
    items, failures = inventory.inventory()
    assert not items and failures[0][0] == 'oversized'


def test_lookup_deadline_covers_real_verified_tls_slow_headers(tmp_path, monkeypatch):
    """Dripping headers never reset the total lookup budget or leave live I/O."""
    import shutil
    import socket
    import subprocess
    import threading
    import time

    network = module('network')
    openssl = shutil.which('openssl')
    if not openssl:
        pytest.skip('The loopback TLS regression needs openssl for its temporary certificate')
    key, cert = tmp_path / 'test.key', tmp_path / 'test.crt'
    subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                    '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1',
                    '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True, timeout=5)
    try:
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
    except PermissionError:
        pytest.skip('The loopback TLS regression needs local socket permission')
    listener.listen(1)
    listener.settimeout(2)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(cert, key)
    client_context = ssl.create_default_context(cafile=str(cert))
    peer_finished = threading.Event()
    def peer():
        try:
            raw, _ = listener.accept()
            with server_context.wrap_socket(raw, server_side=True) as connection:
                connection.settimeout(2)
                connection.recv(4096)
                connection.sendall(b'HTTP/1.1 200 OK\r\n')
                for _ in range(9):
                    time.sleep(.1)
                    connection.sendall(b'X-Slow: yes\r\n')
                connection.sendall(b'Content-Length: 7\r\n\r\n8.8.8.8')
        except (OSError, TimeoutError):
            pass
        finally:
            peer_finished.set()
    worker = threading.Thread(target=peer, daemon=True)
    worker.start()
    monkeypatch.setattr(network, 'LOOKUP_URL', 'https://127.0.0.1:' + str(listener.getsockname()[1]))
    monkeypatch.setattr(network, 'LOOKUP_TIMEOUT', .3)
    monkeypatch.setattr(network.ssl, 'create_default_context', lambda: client_context)
    try:
        started = time.monotonic()
        assert network.lookup_ip() is None
        elapsed = time.monotonic() - started
        assert elapsed < .55, f'Header drip bypassed the .3s lookup deadline: {elapsed:.2f}s'
        assert peer_finished.wait(.3), 'Lookup deadline did not close its active TLS connection'
    finally:
        listener.close()
        worker.join(2)


def test_stalled_dns_is_bounded_and_cannot_connect_after_cancellation(monkeypatch):
    import socket
    import threading
    import time

    network = module('network')
    started, release = threading.Event(), threading.Event()
    sockets = []
    def resolve(*args, **kwargs):
        started.set()
        assert release.wait(2)
        return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('8.8.8.8', 443))]
    class LateSocket:
        def __init__(self, *args):
            self.closed = False
            sockets.append(self)
        def close(self):
            self.closed = True
        def connect(self, address):
            pytest.fail('Cancelled DNS lookup must never connect afterwards')
    monkeypatch.setattr(network, 'LOOKUP_TIMEOUT', .1)
    monkeypatch.setattr(network.socket, 'getaddrinfo', resolve)
    monkeypatch.setattr(network.socket, 'socket', LateSocket)
    before = time.monotonic()
    try:
        assert network.lookup_ip() is None
        assert started.is_set()
        assert time.monotonic() - before < .3
    finally:
        release.set()
    deadline = time.monotonic() + 1
    while any(worker.name == 'alphagsm-public-ip' for worker in threading.enumerate()):
        assert time.monotonic() < deadline, 'Cancelled DNS worker did not finish when the resolver returned'
        time.sleep(.01)
    assert all(connection.closed for connection in sockets)


def test_repeated_lookup_does_not_accumulate_workers_while_system_dns_is_stalled(monkeypatch):
    import threading
    import time
    network = module('network')
    release = threading.Event()
    calls = []
    def stalled(budget):
        calls.append(budget)
        assert release.wait(2)
        return None
    monkeypatch.setattr(network, 'LOOKUP_TIMEOUT', .03)
    monkeypatch.setattr(network, '_lookup_exchange', stalled)
    try:
        assert network.lookup_ip() is None
        assert network.lookup_ip() is None
        assert len(calls) == 1, 'A timed-out system resolver spawned another uncancellable worker'
    finally:
        release.set()
    deadline = time.monotonic() + 1
    while any(worker.name == 'alphagsm-public-ip' for worker in threading.enumerate()):
        assert time.monotonic() < deadline
        time.sleep(.01)
