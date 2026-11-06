"""Bounded real DNS refuses partial A success when AAAA cannot be resolved."""
import importlib
import socket
import threading
import time

import pytest
import dns.message
import dns.rdatatype
import dns.rrset
import dns.resolver


def test_dns_real_timeout_discards_partial_family_and_closes_all_workers(monkeypatch):
    assert importlib.util.find_spec('agent.dns_lookup'), 'missing bounded DNS helper'
    module = importlib.import_module('agent.dns_lookup')
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(('127.0.0.1', 0))
    except PermissionError:
        pytest.skip('Local DNS regression needs loopback socket permission')
    server.settimeout(.1)
    stopped = threading.Event()
    questions = []
    def peer():
        while not stopped.is_set():
            try:
                data, address = server.recvfrom(4096)
                request = dns.message.from_wire(data)
                question = request.question[0]
                questions.append(question.rdtype)
                if question.rdtype == dns.rdatatype.A:
                    response = dns.message.make_response(request)
                    response.answer.append(dns.rrset.from_text('game.example.', 60, 'IN', 'A', '8.8.8.8'))
                    server.sendto(response.to_wire(), address)
            except (OSError, dns.exception.DNSException):
                continue
    worker = threading.Thread(target=peer, daemon=True)
    worker.start()
    sync_resolver = dns.resolver.Resolver(configure=False)
    sync_resolver.nameservers = ['127.0.0.1']
    sync_resolver.port = server.getsockname()[1]
    monkeypatch.setattr(module.dns.resolver, 'Resolver', lambda: sync_resolver)
    if hasattr(module.dns, 'asyncresolver'):
        async_resolver = module.dns.asyncresolver.Resolver(configure=False)
        async_resolver.nameservers = ['127.0.0.1']
        async_resolver.port = server.getsockname()[1]
        monkeypatch.setattr(module.dns.asyncresolver, 'Resolver', lambda: async_resolver)
    try:
        for _ in range(3):
            started = time.monotonic()
            with pytest.raises(ValueError, match='timed out'):
                module.resolve_host('game.example', .1)
            assert time.monotonic() - started < .17, 'DNS retry backoff escaped the shared .1s lifetime'
        assert dns.rdatatype.A in questions and dns.rdatatype.AAAA in questions
    finally:
        stopped.set()
        server.close()
        worker.join(1)
