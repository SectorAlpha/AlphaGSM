"""Native Workshop commands remain connected to every Unreal-family lifecycle."""

from importlib import import_module

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer


@pytest.mark.parametrize("name,app", [("conanexiles", 440900), ("ark", 346110),
                                    ("squadserver", 393380), ("squad44server", 736220)])
def test_cleanup_clears_desired_before_next_prestart(name, app, tmp_path):
    """Removing staged mods must not silently re-add them on the next launch."""
    module = import_module(f"gamemodules.{name}")
    server = DummyServer("unrealworkshop")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    state = module.ensure_mod_state(server)
    state["desired"]["workshop"] = [{"workshop_id": "111"}]
    module.cleanup_configured_mods(server)
    module.prestart(server)
    assert state["desired"]["workshop"] == []
    assert state["native_workshop"]["workshop_ids"] == []
    assert module.workshop_app_id == app
    assert "mod" in module.commands


@pytest.mark.parametrize("name", ["conanexiles", "ark", "squadserver", "squad44server"])
def test_prestart_respects_explicit_autoapply_opt_out(name, tmp_path, monkeypatch):
    """An operator opting out of automatic apply can stage explicitly later."""
    module = import_module(f"gamemodules.{name}")
    server = DummyServer("unrealworkshop")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    state = module.ensure_mod_state(server)
    state["desired"]["workshop"] = [{"workshop_id": "111"}]
    state["autoapply"] = False
    def unexpected(_server):
        raise AssertionError("disabled automatic apply invoked Workshop downloads")
    monkeypatch.setattr(module, "apply_configured_mods", unexpected)
    module.prestart(server)
    assert state["desired"]["workshop"] == [{"workshop_id": "111"}]


@pytest.mark.parametrize("name", ["squadserver", "squad44server"])
def test_squad_info_uses_explicit_real_query_port(name, tmp_path):
    """An explicit query-port change must also change the info protocol endpoint."""
    module = import_module(f"gamemodules.{name}")
    server = DummyServer("squadquery")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    key, protocol = ("rconport", "squad_rcon") if name == "squadserver" else ("queryport", "a2s")
    server.data[key] = "28212"
    assert module.get_info_address(server) == ("127.0.0.1", 28212, protocol)
