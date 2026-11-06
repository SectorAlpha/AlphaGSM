"""A final report cannot hold local policy mutations behind slow HTTPS headers."""
import shutil
import socket
import ssl
import subprocess
import threading
import time

import pytest

from agent.config import Config
from agent.service import Service
from agent.transport import Transport, TransportError
import agent.transport as transport_module
from test_preflight import runtime


@pytest.fixture
def slow_report_peer(tmp_path):
    openssl = shutil.which('openssl')
    if not openssl:
        pytest.skip('Loopback TLS regression needs openssl')
    key, cert = tmp_path / 'peer.key', tmp_path / 'peer.crt'
    subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
        '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1', '-keyout', str(key), '-out', str(cert)],
        check=True, capture_output=True, timeout=5)
    try:
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
    except PermissionError:
        pytest.skip('Loopback TLS regression needs local socket permission')
    listener.listen(1)
    listener.settimeout(2)
    server_tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_tls.load_cert_chain(cert, key)
    client_tls = ssl.create_default_context(cafile=str(cert))
    seen, finished, stopped = threading.Event(), threading.Event(), threading.Event()
    def peer():
        try:
            raw, _ = listener.accept()
            with server_tls.wrap_socket(raw, server_side=True) as connection:
                connection.settimeout(2)
                connection.recv(4096)
                seen.set()
                connection.sendall(b'HTTP/1.1 200 OK\r\n')
                for _ in range(9):
                    if stopped.wait(.1):
                        return
                    connection.sendall(b'X-Slow: yes\r\n')
                connection.sendall(b'Content-Length: 17\r\n\r\n{"accepted":true}')
        except OSError:
            pass
        finally:
            finished.set()
    worker = threading.Thread(target=peer, daemon=True)
    worker.start()
    try:
        yield 'https://127.0.0.1:' + str(listener.getsockname()[1]), client_tls, seen, finished
    finally:
        stopped.set()
        listener.close()
        worker.join(2)


def test_report_deadline_interrupts_real_tls_dripping_headers(slow_report_peer):
    origin, context, _, finished = slow_report_peer
    transport = Transport(origin, context=context)
    started = time.monotonic()
    with pytest.raises(TransportError):
        transport.request('POST', '/v1/agent/reports', payload={}, timeout=.3)
    assert time.monotonic() - started < .55, 'Report header drip escaped its total .3s deadline'
    assert finished.wait(.3), 'Timed-out report did not close active TLS I/O'


def test_final_report_policy_lock_is_released_at_hard_network_budget(tmp_path, slow_report_peer, monkeypatch):
    origin, context, seen, _ = slow_report_peer
    monkeypatch.setattr(transport_module, 'REPORT_TIMEOUT', .3, raising=False)
    cfg = Config(tmp_path / 'agent')
    cfg.enroll(origin, dict(schema_version=1, installation_id='i', credential_generation=1,
        reporting=dict(key_id='r', secret='r' * 43), management=None))
    cfg.bind('world', 'world', 1, actions=[], publication=True,
        metadata=dict(game_id='minecraft.vanilla', host='8.8.8.8', port=25565, name='World', capacity=20))
    cfg.enable(reporting=True)
    service = Service(cfg, runtime=runtime(), transport=Transport(origin, context=context))
    failures = []
    def report():
        try:
            service.report_once()
        except TransportError as exc:
            failures.append(exc)
    worker = threading.Thread(target=report)
    worker.start()
    try:
        assert seen.wait(2)
        started = time.monotonic()
        cfg.publication('world', False)
        assert time.monotonic() - started < .55, 'Slow report blocked an operator revocation beyond its budget'
        worker.join(1)
        assert not worker.is_alive() and failures
        assert cfg.load()['bindings']['world']['publication'] is False
    finally:
        worker.join(2)


def test_reports_keep_fake_opener_boundary_and_only_reports_cap_timeout():
    from types import SimpleNamespace
    context = ssl.create_default_context()
    transport = Transport('https://control.example', context=context)
    assert any(getattr(handler, '_context', None) is context for handler in transport.opener.handlers)
    seen = []
    class Response:
        def __init__(self, request):
            self.request = request
            self.body = b'{"accepted":true}'
            self.fp = SimpleNamespace(raw=SimpleNamespace(_sock=SimpleNamespace(settimeout=lambda value: None)))
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def geturl(self):
            return self.request.full_url
        def read1(self, limit):
            chunk, self.body = self.body[:limit], self.body[limit:]
            return chunk
    def open_request(request, timeout):
        seen.append((request, timeout))
        return Response(request)
    transport.opener = SimpleNamespace(open=open_request)
    assert transport.request('POST', '/v1/agent/reports', payload={}, timeout=99) == {'accepted': True}
    assert 0 < seen[0][1] <= 10
    assert seen[0][0].agent_deadline.family == socket.AF_UNSPEC
    assert transport.request('GET', '/v1/agent/jobs', timeout=35) == {'accepted': True}
    assert seen[1][1] == 35 and not hasattr(seen[1][0], 'agent_deadline')


def test_generic_deadline_connection_preserves_provider_ipv6(monkeypatch):
    from agent import http_deadline
    seen = []
    def resolve(host, port, **kwargs):
        assert kwargs['family'] == socket.AF_UNSPEC
        return [(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', ('::1', port, 0, 0))]
    class Connection:
        def __init__(self, family, kind, protocol):
            assert family == socket.AF_INET6
        def settimeout(self, timeout):
            assert 0 < timeout <= 1
        def connect(self, destination):
            seen.append(destination)
        def shutdown(self, how):
            assert how == socket.SHUT_RDWR
        def close(self):
            pass
    monkeypatch.setattr(http_deadline.socket, 'getaddrinfo', resolve)
    monkeypatch.setattr(http_deadline.socket, 'socket', Connection)
    budget = http_deadline.DeadlineBudget(1)
    budget.connect(('control.example', 443))
    budget.cancel()
    assert seen == [('::1', 443, 0, 0)]


@pytest.mark.parametrize('removed_legacy_attribute', [False, True])
def test_deadline_https_handler_supports_python312_without_check_hostname_keyword(monkeypatch, removed_legacy_attribute):
    from agent import http_deadline
    import urllib.request
    context = ssl.create_default_context()
    budget = http_deadline.DeadlineBudget(1)
    handler = http_deadline.DeadlineHTTPSHandler(budget, context=context)
    if removed_legacy_attribute and hasattr(handler, '_check_hostname'):
        del handler._check_hostname
    calls = []
    class ModernConnection:
        def __init__(self, supplied_budget, host, *, context=None, timeout=None):
            calls.append((supplied_budget, host, context, timeout))
    monkeypatch.setattr(http_deadline, 'DeadlineHTTPSConnection', ModernConnection)
    def do_open(connection, request, **kwargs):
        assert request.full_url == 'https://control.example/v1/agent/reports'
        return connection('control.example', timeout=1, **kwargs)
    monkeypatch.setattr(handler, 'do_open', do_open)
    handler.https_open(urllib.request.Request('https://control.example/v1/agent/reports'))
    assert calls == [(budget, 'control.example', context, 1)]
    assert context.check_hostname is True and context.verify_mode == ssl.CERT_REQUIRED
