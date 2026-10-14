"""Remote Wreckfest diagnostics must distinguish protocol replies from listeners."""

import socket
import struct

import pytest

from tests.smoke_tests import wreckfestserver_diagnostics as diagnostics


class _Socket:
    def __init__(self, packets):
        self.packets = iter(packets)
        self.sent = []
        self.address = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def settimeout(self, _timeout):
        pass

    def connect(self, address):
        self.address = address

    def send(self, packet):
        self.sent.append(packet)

    def recv(self, _size):
        return next(self.packets)


def test_ipv6_diagnostic_accepts_only_challenge_then_native_info(monkeypatch):
    info = b"\xff\xff\xff\xffI\x11Native name\0native_track\0wreckfest\0Wreckfest\0\x1c\x7c\x02\x10\0"
    transport = _Socket([b"\xff\xff\xff\xffA1234", info])
    families = []
    monkeypatch.setattr(diagnostics.socket, "socket", lambda family, _kind: families.append(family) or transport)
    result = diagnostics.probe_a2s(socket.AF_INET6, "::1", 19642)
    assert families == [socket.AF_INET6]
    assert transport.address == ("::1", 19642)
    assert transport.sent == [diagnostics.INFO_REQUEST, diagnostics.INFO_REQUEST + b"1234"]
    assert result["protocol"] == "a2s"
    assert (result["name"], result["map"], result["players"], result["max_players"]) == (
        "Native name", "native_track", 2, 16)


def test_arbitrary_udp_reply_is_not_a2s_health(monkeypatch):
    transport = _Socket([b"listener is alive"])
    monkeypatch.setattr(diagnostics.socket, "socket", lambda *_: transport)
    result = diagnostics.probe_a2s(socket.AF_INET, "127.0.0.1", 19642)
    assert "protocol" not in result
    assert result["packet_prefix"] == b"listener is alive".hex()


def test_truncated_info_is_not_native_health(monkeypatch):
    transport = _Socket([b"\xff\xff\xff\xffI\x11partial"])
    monkeypatch.setattr(diagnostics.socket, "socket", lambda *_: transport)
    result = diagnostics.probe_a2s(socket.AF_INET, "127.0.0.1", 19642)
    assert "protocol" not in result
    assert result["error"] == "Malformed A2S_INFO response"


def test_socket_diagnostic_reads_per_socket_v6only_without_inference():
    message = bytearray(72)
    message[0] = socket.AF_INET6
    message[4:6] = struct.pack("!H", 19642)
    message[68:72] = struct.pack("=I", 991)
    attribute = struct.pack("=HHB", 5, 11, 1) + b"\0\0\0"
    assert diagnostics.decode_inet_diag(bytes(message) + attribute, 19642) == {
        "address": "::", "port": 19642, "inode": 991, "v6only": True}
    assert diagnostics.decode_inet_diag(bytes(message), 19642)["v6only"] is None
    assert diagnostics.decode_inet_diag(bytes(message) + attribute, 27016) is None


def test_native_log_tail_keeps_network_evidence_and_omits_secrets():
    source = "bind query port 27016\nAuth ticket=secret\npassword=secret port=27016\nIPv6 socket ready\nunrelated settings\n"
    assert diagnostics.safe_network_tail(source) == "bind query port 27016\nIPv6 socket ready"


def test_raknet_observer_correlates_nonce_and_bounds_disposable_payload(monkeypatch):
    nonce = b"N" * 8
    payload = b"x" * 900
    transport = _Socket([b"\x1c" + nonce + b"G" * 8 + diagnostics.RAKNET_MAGIC + payload])
    monkeypatch.setattr(diagnostics.secrets, "token_bytes", lambda _length: nonce)
    monkeypatch.setattr(diagnostics.socket, "socket", lambda *_: transport)
    result = diagnostics.probe_raknet(socket.AF_INET6, "::1", 19642)
    assert transport.sent == [b"\x01" + nonce + diagnostics.RAKNET_MAGIC + nonce]
    assert result["protocol"] == "raknet"
    assert result["nonce_matched"] is True
    assert result["server_guid"] == (b"G" * 8).hex()
    assert result["payload_bytes"] == 900
    assert result["payload_hex"] == payload[:512].hex()


@pytest.mark.parametrize("packet", [
    b"\x1c" + b"X" * 8 + b"G" * 8 + bytes.fromhex("00ffff00fefefefefdfdfdfd12345678"),
    b"\x1c" + b"N" * 8 + b"G" * 8 + b"bad-magic-padding",
    b"\x1b" + b"N" * 8 + b"G" * 8 + bytes.fromhex("00ffff00fefefefefdfdfdfd12345678"),
    b"\x1c" + b"N" * 8,
])
def test_raknet_observer_rejects_stale_or_unrelated_datagrams(monkeypatch, packet):
    transport = _Socket([packet])
    monkeypatch.setattr(diagnostics.secrets, "token_bytes", lambda _length: b"N" * 8)
    monkeypatch.setattr(diagnostics.socket, "socket", lambda *_: transport)
    result = diagnostics.probe_raknet(socket.AF_INET, "127.0.0.1", 27017)
    assert "protocol" not in result
    assert "payload_hex" not in result


def test_snapshot_observes_three_raknet_ports_in_each_address_family(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(diagnostics, "probe_a2s", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(diagnostics, "probe_raknet", lambda family, address, port, **kwargs:
                        calls.append((family, address, port, kwargs["timeout"])) or {})
    monkeypatch.setattr(diagnostics, "_native_details", lambda _: {})
    monkeypatch.setattr(diagnostics, "_bounded_text", lambda *_args, **_kwargs: "0")
    monkeypatch.setattr(diagnostics, "_socket_v6only", lambda _: {})
    monkeypatch.setattr(diagnostics.shutil, "which", lambda _: None)
    result = diagnostics.snapshot(19642, tmp_path, quick=True, gameport=28752)
    assert len(result["raknet"]) == 9
    assert {(family, address, port) for family, address, port, _timeout in calls} == {
        (family, address, port) for port in (19642, 28752, 27017) for family, address in (
            (socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1"),
            (socket.AF_INET6, "::ffff:127.0.0.1"))}
    assert all(timeout == 0.2 for _, _, _, timeout in calls)
