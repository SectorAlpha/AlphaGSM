import errno
import json
from types import SimpleNamespace

import server.port_manager as port_manager
import server.server as server_module
import server.runtime as runtime_module


class DummyData(dict):
    def save(self):
        return None


def make_server(name, payload, *, module=None):
    return SimpleNamespace(
        name=name,
        data=DummyData(payload),
        module=module or SimpleNamespace(),
    )


def test_normalize_hosted_ip_and_overlap_handle_local_wildcards():
    assert port_manager.normalize_hosted_ip("") == "0.0.0.0"
    assert port_manager.normalize_hosted_ip("localhost") == "127.0.0.1"
    assert port_manager.hosted_ips_overlap("0.0.0.0", "127.0.0.1")
    assert port_manager.hosted_ips_overlap("127.0.0.1", "0.0.0.0")
    assert not port_manager.hosted_ips_overlap("127.0.0.1", "192.0.2.10")


def test_collect_claim_set_includes_stored_ports_and_deduplicates_runtime_and_hook_claims():
    module = SimpleNamespace(
        get_query_address=lambda server: ("127.0.0.1", server.data["port"] + 2, "a2s"),
        get_info_address=lambda server: ("127.0.0.1", server.data["port"] + 2, "a2s"),
    )
    server = make_server(
        "alpha",
        {
            "port": 27017,
            "queryport": 27018,
            "bindaddress": "",
            "publicip": "203.0.113.10",
            "ports": [{"host": 27017, "container": 27017, "protocol": "udp"}],
        },
        module=module,
    )

    claim_set = port_manager.collect_claim_set(server)
    hook_endpoints = [
        endpoint
        for endpoint in claim_set.endpoints
        if endpoint.source_key.startswith("hook:")
    ]

    assert ("internal", "0.0.0.0", 27017, "port") in {
        (endpoint.scope, endpoint.ip, endpoint.port, endpoint.source_key)
        for endpoint in claim_set.endpoints
    }
    assert ("external", "203.0.113.10", 27017, "runtime:ports") not in {
        (endpoint.scope, endpoint.ip, endpoint.port, endpoint.source_key)
        for endpoint in claim_set.endpoints
    }
    assert len(hook_endpoints) == 1
    assert hook_endpoints[0].scope == "internal"
    assert hook_endpoints[0].ip == "127.0.0.1"
    assert hook_endpoints[0].port == 27019


def test_collect_claim_set_uses_overrides_when_calling_hooks():
    module = SimpleNamespace(
        get_query_address=lambda server: ("127.0.0.1", server.data["port"] + 1, "a2s"),
    )
    server = make_server(
        "alpha",
        {"module": "tf2", "port": 27015},
        module=module,
    )

    claim_set = port_manager.collect_claim_set(server, overrides={"port": 27020})

    assert any(
        endpoint.source_key == "hook:get_query_address" and endpoint.port == 27021
        for endpoint in claim_set.endpoints
    )


def test_collect_claim_set_rebuilds_runtime_ports_from_overrides():
    module = SimpleNamespace(
        get_container_spec=lambda server: {
            "ports": [
                {
                    "host": int(server.data["port"]) + 1,
                    "container": int(server.data["port"]) + 1,
                    "protocol": "udp",
                }
            ]
        }
    )
    server = make_server(
        "alpha",
        {
            "module": "tf2",
            "port": 27015,
            "ports": [{"host": 27016, "container": 27016, "protocol": "udp"}],
        },
        module=module,
    )

    claim_set = port_manager.collect_claim_set(server, overrides={"port": 27030})

    runtime_ports = [
        endpoint.port
        for endpoint in claim_set.endpoints
        if endpoint.source_key == "runtime:ports"
    ]

    assert runtime_ports == [27031]
    assert 27016 not in runtime_ports


def test_runtime_port_endpoints_ignores_preinstall_server_errors(monkeypatch):
    module = SimpleNamespace(
        get_start_command=lambda server: (_ for _ in ()).throw(
            server_module.ServerError("Executable file not found")
        )
    )
    server = make_server("alpha", {"module": "tf2", "port": 27015}, module=module)

    monkeypatch.setattr(runtime_module, "get_container_spec", lambda temp_server: module.get_start_command(temp_server))

    endpoints = port_manager._runtime_port_endpoints(
        server,
        module,
        {"external_ip": "0.0.0.0", "port": 27015},
        allow_stale_saved_ports=False,
    )

    assert endpoints == []


def test_collect_claim_set_lazily_loads_missing_module_for_hooks(monkeypatch):
    module = SimpleNamespace(
        get_query_address=lambda server: ("127.0.0.1", server.data["port"] + 1, "a2s"),
    )
    server = SimpleNamespace(
        name="alpha",
        data=DummyData({"module": "tf2", "port": 27015}),
        module=None,
    )
    seen = []

    def fake_findmodule(name):
        seen.append(name)
        return name, module

    monkeypatch.setattr(server_module, "_findmodule", fake_findmodule)

    claim_set = port_manager.collect_claim_set(server)

    assert seen == ["tf2"]
    assert any(
        endpoint.source_key == "hook:get_query_address" and endpoint.port == 27016
        for endpoint in claim_set.endpoints
    )


def test_collect_claim_set_propagates_unexpected_hook_errors():
    module = SimpleNamespace(get_query_address=lambda server: 1 / 0)
    server = make_server("alpha", {"port": 27015}, module=module)

    try:
        port_manager.collect_claim_set(server)
    except ZeroDivisionError:
        pass
    else:
        raise AssertionError("ZeroDivisionError should not be swallowed")


def test_resolve_module_name_propagates_unexpected_resolution_errors(monkeypatch):
    monkeypatch.setattr(server_module, "_findmodule", lambda name: (_ for _ in ()).throw(ValueError("boom")))

    try:
        port_manager._resolve_module_name("tf2")
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError should not be swallowed")


def test_resolve_module_name_fallback_uses_catalog(monkeypatch):
    fake_module = SimpleNamespace(__file__="/tmp/teamfortress2.py")

    class FakeCatalog:
        def resolve(self, name):
            assert name == "tf2server"
            return "teamfortress2"

    def fake_import(name):
        if name != "gamemodules.teamfortress2":
            raise ImportError(name)
        return fake_module

    monkeypatch.setattr(port_manager, "MODULE_CATALOG", FakeCatalog(), raising=False)
    monkeypatch.setattr(port_manager, "import_module", fake_import)
    monkeypatch.setattr(port_manager, "SERVERMODULEPACKAGE", "gamemodules.")
    monkeypatch.setattr(port_manager.runtime_module, "ensure_runtime_hooks", lambda module: None)

    resolved = port_manager._resolve_module_name_fallback("tf2server")

    assert resolved is fake_module


def test_detect_conflicts_requires_matching_scope(monkeypatch):
    current = make_server(
        "alpha",
        {"port": 27015, "bindaddress": "127.0.0.1", "publicip": "10.0.0.1"},
    )
    other = make_server(
        "bravo",
        {"port": 27015, "bindaddress": "10.0.0.2", "publicip": "127.0.0.1"},
    )

    monkeypatch.setattr(port_manager, "iter_managed_servers", lambda server: [other])
    monkeypatch.setattr(port_manager, "probe_live_listener", lambda ip, port: False)

    conflicts = port_manager.detect_conflicts(current, include_live=False)

    assert conflicts == []


def test_detect_conflicts_keeps_internal_wildcard_overlap(monkeypatch):
    current = make_server(
        "alpha",
        {"port": 27015, "bindaddress": "0.0.0.0", "publicip": "10.0.0.1"},
    )
    other = make_server(
        "bravo",
        {"port": 27015, "bindaddress": "127.0.0.1", "publicip": "10.0.0.2"},
    )

    monkeypatch.setattr(port_manager, "iter_managed_servers", lambda server: [other])
    monkeypatch.setattr(port_manager, "probe_live_listener", lambda ip, port: False)

    conflicts = port_manager.detect_conflicts(current, include_live=False)

    assert any(conflict.kind == "managed" for conflict in conflicts)


def test_detect_conflicts_does_not_apply_wildcard_overlap_to_external_scope(
    monkeypatch,
):
    current = make_server(
        "alpha",
        {"port": 27015, "bindaddress": "127.0.0.1", "publicip": "0.0.0.0"},
    )
    other = make_server(
        "bravo",
        {"port": 27015, "bindaddress": "10.0.0.2", "publicip": "127.0.0.1"},
    )

    monkeypatch.setattr(port_manager, "iter_managed_servers", lambda server: [other])
    monkeypatch.setattr(port_manager, "probe_live_listener", lambda ip, port: False)

    conflicts = port_manager.detect_conflicts(current, include_live=False)

    assert conflicts == []


def test_probe_live_listener_treats_eaddrnotavail_as_unclaimed(monkeypatch):
    class FakeSocket:
        def __init__(self, *args):
            self.bound = None

        def bind(self, sockaddr):
            raise OSError(errno.EADDRNOTAVAIL, "Cannot assign requested address")

        def close(self):
            return None

    monkeypatch.setattr(
        port_manager.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(port_manager.socket.AF_INET, port_manager.socket.SOCK_STREAM, 0, "", ("203.0.113.10", 27015))],
    )
    monkeypatch.setattr(port_manager.socket, "socket", lambda *args, **kwargs: FakeSocket())

    assert port_manager.probe_live_listener("203.0.113.10", 27015) is False


def test_detect_conflicts_reports_matching_scope_collisions(monkeypatch):
    current = make_server("alpha", {"port": 27015, "bindaddress": "127.0.0.1"})
    other = make_server("bravo", {"port": 27015, "bindaddress": "127.0.0.1"})

    monkeypatch.setattr(port_manager, "iter_managed_servers", lambda server: [other])
    monkeypatch.setattr(port_manager, "probe_live_listener", lambda ip, port: False)

    conflicts = port_manager.detect_conflicts(current, include_live=False)

    assert {conflict.kind for conflict in conflicts} == {"managed"}
    assert any(conflict.managed_server == "bravo" for conflict in conflicts)
    assert "bravo" in port_manager.describe_conflicts(conflicts)


def test_recommend_shift_moves_the_whole_port_group_together(monkeypatch):
    server = make_server(
        "alpha",
        {"port": 27015, "queryport": 27016, "steamport": 27020},
    )

    monkeypatch.setattr(
        port_manager,
        "detect_conflicts",
        lambda current, overrides=None, **kwargs: [object()]
        if overrides
        in (
            {"port": 27016, "queryport": 27017, "steamport": 27021},
            {"port": 27014, "queryport": 27015, "steamport": 27019},
        )
        else [],
    )

    recommendation = port_manager.recommend_shift(server)

    assert recommendation.offset == 2
    assert recommendation.values == {
        "port": 27017,
        "queryport": 27018,
        "steamport": 27022,
    }


def test_iter_managed_servers_uses_alpha_resolution_path_and_skips_missing_modules(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "alpha.json").write_text(json.dumps({"module": "tf2"}))
    (tmp_path / "bravo.json").write_text(json.dumps({"name": "bravo"}))

    seen = []
    resolved = SimpleNamespace(name="tf2")

    monkeypatch.setattr(server_module, "DATAPATH", str(tmp_path))
    monkeypatch.setattr(
        server_module,
        "_findmodule",
        lambda module_name: (seen.append(module_name) or module_name, resolved),
    )

    managed = list(port_manager.iter_managed_servers(make_server("charlie", {})))

    assert seen == ["tf2"]
    assert len(managed) == 2
    assert managed[0].module is resolved
    assert managed[1].module is None
