"""Local contract: every file-based BYO module must name a native status protocol.

This test does not download games or log in. The lifecycle runner uses the same
protocol set when it checks a live server.
"""

import pytest

from catalog import byo_servers
from test_auth_byo_contracts import _import_module


# Protocols implemented by server.Server.query / info. Generic tcp and udp
# reachability are not game status.
NATIVE_PROTOCOLS = frozenset({
    "a2s",
    "bedrock",
    "http_status",
    "quake",
    "quake2",
    "quakeworld",
    "reclaimer_rcon",
    "robust_status",
    "slp",
    "soldat",
    "source_rcon",
    "squad_rcon",
    "terraria",
    "ts3",
    "ut3",
})

FILE_BYO_CATEGORIES = {"assets", "export", "url", "config"}


def _file_byo_rows():
    return tuple(row for row in byo_servers() if row["category"] in FILE_BYO_CATEGORIES)


def _server(port=27999):
    return type("Server", (), {
        "name": "local",
        "data": {
            "port": port,
            "queryport": port,
            "dir": "/tmp/alphagsm-byo-contract",
            "hostname": "local",
        },
    })()


def _address(module, hook_name, server):
    hook = getattr(module, hook_name, None)
    assert callable(hook), hook_name + " is missing"
    address = hook(server)
    assert isinstance(address, tuple) and len(address) == 3, hook_name
    host, port, protocol = address
    assert host
    assert int(port) > 0
    assert protocol in NATIVE_PROTOCOLS, protocol
    return address


@pytest.mark.parametrize("row", _file_byo_rows(), ids=lambda row: row["module"])
def test_file_byo_module_declares_native_query_and_info(row):
    """Query and info must use the same implemented game-status protocol."""

    module = _import_module(row["module"])
    server = _server()
    query = _address(module, "get_query_address", server)
    info = _address(module, "get_info_address", server)
    assert info[2] == query[2]
