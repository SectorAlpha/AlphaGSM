"""Native Tripwire Workshop activation remains part of the module lifecycle."""
from importlib import import_module

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer
from server import ServerError


@pytest.mark.parametrize("game,consumer", [("kf2server", 232090), ("rs2server", 418460)])
def test_native_prestart_uses_desired_ids_and_cleanup_does_not_reactivate(game, consumer, monkeypatch):
    module = import_module(f"gamemodules.{game}.main")
    server = DummyServer("tripwire")
    server.data["mods"] = {"enabled": True, "autoapply": True,
                           "desired": {"workshop": [{"workshop_id": "111"}]}}
    calls = []
    monkeypatch.setattr(module, "apply_configured_mods", lambda current: calls.append(current))
    monkeypatch.setattr(module, "sync_server_config", lambda _current: None, raising=False)
    module.prestart(server)
    assert calls == [server]
    assert module.workshop_app_id == consumer
    assert "mod" in module.commands
    server.data["mods"]["autoapply"] = False
    module.prestart(server)
    assert calls == [server]


@pytest.mark.parametrize("game", ["kf2server", "rs2server"])
def test_explicit_runtime_wrappers_keep_all_native_ports(game, monkeypatch):
    module = import_module(f"gamemodules.{game}.main")
    server = DummyServer("tripwire")
    server.data.update(port=28000, queryport=28100)
    captured = {}
    def requirements(_server, **kwargs):
        captured.update(kwargs)
        return {"family": kwargs.get("family", "wine-proton")}
    builder = module.runtime_module if game == "kf2server" else module.proton
    monkeypatch.setattr(builder, "build_runtime_requirements" if game == "kf2server"
                        else "get_runtime_requirements", requirements)
    module.get_runtime_requirements(server)
    assert any(port["key"] == "queryport" and port["protocol"] == "udp"
               for port in captured["port_definitions"])


def test_kf2_native_steam_port_is_claimed_and_published():
    module = import_module("gamemodules.kf2server.main")
    assert {"key": "port", "offset": 12783, "protocol": "udp"} in module.port_claim_definitions


@pytest.mark.parametrize("game,root,suffix,stock", [
    ("kf2server", "KFGame", ".kfm", "KF-BioticsLab"),
    ("rs2server", "ROGame", ".roe", "VNTE-CuChi"),
])
def test_map_selection_requires_native_installed_content(game, root, suffix, stock, tmp_path):
    module = import_module(f"gamemodules.{game}.main")
    server = DummyServer("tripwire")
    server.data["dir"] = str(tmp_path)
    assert module.checkvalue(server, ["startmap"], stock) == stock
    with pytest.raises(ServerError):
        module.checkvalue(server, ["startmap"], "Workshop-Missing")
    installed = tmp_path / root / "Cache/111/Maps" / ("Workshop-Present" + suffix)
    installed.parent.mkdir(parents=True)
    installed.write_bytes(b"cooked map")
    assert module.checkvalue(server, ["startmap"], "Workshop-Present") == "Workshop-Present"
    with pytest.raises(ServerError):
        module.checkvalue(server, ["startmap"], "../Workshop-Present")
