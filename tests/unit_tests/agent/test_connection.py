"""The agent socket names a job; execution still uses the HTTPS job, authorize, and result calls."""

import socket
import threading
import time
from contextlib import nullcontext

from agent.service import Service
from agent.socket_channel import SocketChannel, _accept_value
from agent.transport import AgentLimit
from test_agent import config
from test_contracts import job


class FakeChannel:
    def __init__(self, frames, stop):
        self.frames = list(frames)
        self.sent = []
        self.stop = stop

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def recv(self, timeout):
        if self.frames:
            item = self.frames.pop(0)
            if isinstance(item, BaseException):
                raise item
            return item
        self.stop.wait(timeout)
        return None

    def send(self, payload):
        self.sent.append(payload)


class Runtime:
    def __init__(self, channel, service, errors):
        self.channel = channel
        self.service = service
        self.errors = errors
        self.calls = []
        self._state = "stopped"

    def lock(self, _tag):
        return nullcontext()

    def state(self, _tag):
        return self._state

    def execute(self, _tag, action):
        self.calls.append(action)
        self._state = "running" if action == "start" else "stopped"
        deadline = time.monotonic() + 2
        while not self.channel.sent and time.monotonic() < deadline:
            time.sleep(0.01)
        if not self.channel.sent:
            self.errors.append("heartbeat")
        self.service.stop.set()


def test_request_frame_runs_the_fetched_job_not_the_frame(tmp_path):
    cfg = config(tmp_path)
    errors = []
    channel = FakeChannel([{"type": "request", "job_id": "other-job", "action": "stop"}], threading.Event())
    runtime = Runtime(channel, None, errors)
    sent = []

    def request(method, path, **kwargs):
        sent.append((method, path, kwargs.get("query")))
        if method == "GET":
            queued = job()
            queued["action"] = "start"
            queued["installation_id"] = "install-1"
            queued["policy_version"] = cfg.load()["policy_version"]
            return {"job": queued}
        if path.endswith("/authorize"):
            return {"authorized": True}
        return {"accepted": True}

    service = Service(
        cfg,
        runtime=runtime,
        transport=type("Transport", (), {"request": staticmethod(request)})(),
        channel_factory=lambda _cfg, _session: channel,
    )
    runtime.service = service
    channel.stop = service.stop
    service.heartbeat_interval = 0.05
    assert service._connection_once() == "socket"
    assert runtime.calls == ["start"]
    assert ("GET", "/v1/agent/jobs", "wait=0") in sent
    assert not errors


def test_socket_failure_uses_one_rest_poll_only_when_management_is_enabled(tmp_path):
    cfg = config(tmp_path)
    calls = []

    def factory(_cfg, _session):
        raise OSError("socket down")

    service = Service(cfg, transport=object(), channel_factory=factory)
    service.management_once = lambda wait=25: calls.append(wait)
    assert service._connection_once() == "fallback"
    assert calls == [25]
    cfg.enable(management=False)
    calls.clear()
    assert service._connection_once() == "retry"
    assert calls == []


def test_missing_reporting_key_skips_the_socket(tmp_path):
    cfg = __import__("agent.config", fromlist=["Config"]).Config(tmp_path / "agent")
    cfg.enroll(
        "https://control.example",
        dict(
            schema_version=1,
            installation_id="install-1",
            credential_generation=1,
            reporting=None,
            management=dict(key_id="manage-key", secret="y" * 43),
        ),
    )
    cfg.enable(management=True)
    calls = []

    def factory(_cfg, _session):
        raise AssertionError("socket opened without a reporting key")

    service = Service(cfg, transport=object(), channel_factory=factory)
    service.management_once = lambda wait=25: calls.append(wait)
    assert service._connection_once() == "rest"
    assert calls == [25]


def test_agent_limit_backs_off_without_a_rest_poll(tmp_path):
    cfg = config(tmp_path)
    calls = []

    def factory(_cfg, _session):
        raise AgentLimit("Live agent cap reached")

    service = Service(cfg, transport=object(), channel_factory=factory)
    service.management_once = lambda wait=25: calls.append(wait)
    waits = []

    class Stop:
        def is_set(self):
            return len(waits) >= 1

        def wait(self, timeout):
            waits.append(timeout)
            return True

        def set(self):
            waits.append("set")

    service.stop = Stop()
    service._management_loop()
    assert calls == []
    assert waits[0] >= 60


def _read_exact(conn, size):
    data = b""
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise OSError("closed")
        data += chunk
    return data


def _read_client_frame(conn):
    first, second = _read_exact(conn, 2)
    assert first & 0x80 and second & 0x80
    length = second & 0x7F
    if length == 126:
        length = int.from_bytes(_read_exact(conn, 2), "big")
    mask = _read_exact(conn, 4)
    payload = _read_exact(conn, length)
    return bytes(item ^ mask[index % 4] for index, item in enumerate(payload))


def test_socket_channel_posts_the_reporting_key_and_reads_a_request(tmp_path):
    del tmp_path
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    seen = []

    def serve():
        conn, _addr = listener.accept()
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                data += conn.recv(1024)
            head = data.split(b"\r\n\r\n", 1)[0].decode()
            headers = {}
            for line in head.split("\r\n")[1:]:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
            seen.append(headers["authorization"])
            seen.append(headers["x-agent-session"])
            accept = _accept_value(headers["sec-websocket-key"])
            conn.sendall(
                (
                    "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                    "Connection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n" % accept
                ).encode()
            )
            body = b'{"type":"request","job_id":"job-1","action":"stop"}'
            conn.sendall(bytes((0x81, len(body))) + body)
            assert _read_client_frame(conn) == b'{"type":"heartbeat"}'
        finally:
            conn.close()

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        channel = SocketChannel(
            "https://control.example",
            {"key_id": "report-key", "secret": "x" * 43},
            "abc123",
            connector=lambda: socket.create_connection(("127.0.0.1", port), timeout=2),
        )
        with channel as opened:
            assert opened.recv(2) == {"type": "request", "job_id": "job-1", "action": "stop"}
            opened.send({"type": "heartbeat"})
        assert seen == ["Bearer report-key." + "x" * 43, "abc123"]
    finally:
        thread.join(2)
        listener.close()


def test_socket_close_4429_is_the_agent_cap(tmp_path):
    del tmp_path
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]

    def serve():
        conn, _addr = listener.accept()
        try:
            data = b""
            while b"\r\n\r\n" not in data:
                data += conn.recv(1024)
            key = ""
            for line in data.split(b"\r\n\r\n", 1)[0].decode().split("\r\n")[1:]:
                name, value = line.split(":", 1)
                if name.strip().lower() == "sec-websocket-key":
                    key = value.strip()
            accept = _accept_value(key)
            conn.sendall(
                (
                    "HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: %s\r\n\r\n" % accept
                ).encode()
            )
            payload = (4429).to_bytes(2, "big")
            conn.sendall(bytes((0x88, len(payload))) + payload)
        finally:
            conn.close()

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        channel = SocketChannel(
            "https://control.example",
            {"key_id": "report-key", "secret": "x" * 43},
            "abc123",
            connector=lambda: socket.create_connection(("127.0.0.1", port), timeout=2),
        )
        with channel as opened:
            try:
                opened.recv(2)
            except AgentLimit:
                return
            raise AssertionError("expected the agent cap")
    finally:
        thread.join(2)
        listener.close()
