"""Unit tests for explicit Quake-family query/info protocol hooks."""

import gamemodules.q2server as q2server
import gamemodules.q3server as q3server
import gamemodules.q4server as q4server
import gamemodules.qlserver as qlserver
import gamemodules.qwserver as qwserver


class _DummyServer:
    """Minimal server stub exposing the datastore used by hook helpers."""

    def __init__(self, port):
        self.data = {"port": port}


def test_q2server_uses_explicit_quake_protocol():
    server = _DummyServer(27910)
    assert q2server.get_query_address(server) == ("127.0.0.1", 27910, "quake")
    assert q2server.get_info_address(server) == ("127.0.0.1", 27910, "quake")


def test_q3server_uses_explicit_quake_protocol():
    server = _DummyServer(27960)
    assert q3server.get_query_address(server) == ("127.0.0.1", 27960, "quake")
    assert q3server.get_info_address(server) == ("127.0.0.1", 27960, "quake")


def test_q4server_uses_explicit_quake_protocol():
    server = _DummyServer(28004)
    assert q4server.get_query_address(server) == ("127.0.0.1", 28004, "quake")
    assert q4server.get_info_address(server) == ("127.0.0.1", 28004, "quake")


def test_qwserver_uses_explicit_quake_protocol():
    server = _DummyServer(27500)
    assert qwserver.get_query_address(server) == ("127.0.0.1", 27500, "quake")
    assert qwserver.get_info_address(server) == ("127.0.0.1", 27500, "quake")


def test_qlserver_uses_explicit_quake_protocol():
    server = _DummyServer(27960)
    assert qlserver.get_query_address(server) == ("127.0.0.1", 27960, "quake")
    assert qlserver.get_info_address(server) == ("127.0.0.1", 27960, "quake")
