"""Regressions for query routing and Java selection observed in CI."""
from types import SimpleNamespace

import pytest

from gamemodules import mtaserver, ohdserver
from gamemodules.minecraft import velocity


@pytest.mark.parametrize("module,data,port,protocol", [
    (mtaserver, {"port": 22003, "httpport": 22005}, 22005, "tcp"),
    (ohdserver, {"port": 7777, "queryport": 27015}, 27015, "a2s"),
])
def test_queries_follow_runtime_host_for_both_commands(monkeypatch, module, data, port, protocol):
    monkeypatch.setattr(module.runtime_module, "resolve_query_host", lambda _server: "172.17.0.1")
    server = SimpleNamespace(data=data)
    assert module.get_query_address(server) == ("172.17.0.1", port, protocol)
    assert module.get_info_address(server) == ("172.17.0.1", port, protocol)


@pytest.mark.parametrize("version,override,expected", [
    ("4.0.0", None, 25), ("4.0.0-SNAPSHOT", None, 25),
    ("3.4.0", None, 21), (None, None, 25), ("4.0.0", 25, 25),
])
def test_velocity_java_version_uses_proxy_version_scheme(monkeypatch, version, override, expected):
    server = SimpleNamespace(data={"version": version, "java_major": override})
    monkeypatch.setattr(velocity.runtime_module, "build_runtime_requirements", lambda _server, **kwargs: kwargs)
    requirements = velocity.get_runtime_requirements(server)
    assert requirements["extra"]["java"] == expected
    assert requirements["env"]["ALPHAGSM_JAVA_MAJOR"] == str(expected)
