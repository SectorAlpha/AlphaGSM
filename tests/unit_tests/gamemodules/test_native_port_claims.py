"""Keep native adjacent listeners owned even for process-backed servers."""

from importlib import import_module
from types import SimpleNamespace

import pytest

from server.port_manager import collect_claim_set


@pytest.mark.parametrize("module_name,offsets", [
    ("argoserver", (0, 1, 2)),
    ("lifeisfeudalserver", (0, 1, 2)),
    ("solserver", (0, 10)),
])
def test_native_auxiliary_process_ports_are_claimed(module_name, offsets, monkeypatch):
    module = import_module("gamemodules." + module_name)
    monkeypatch.setattr(module.runtime_module, "resolve_query_host", lambda _s: "127.0.0.1")
    server = SimpleNamespace(name="native", module=module,
                             data={"port": 29000, "runtime": {"backend": "process"}})
    claims = collect_claim_set(server)
    assert {29000 + offset for offset in offsets} <= {item.port for item in claims.endpoints}
