"""Squad-family Workshop plugin containment and native payload selection."""

from importlib import import_module
import json

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


@pytest.fixture(params=[("squadserver", "SquadGame", 393380),
                       ("squad44server", "PostScriptum", 736220)])
def plugin_server(request, tmp_path, monkeypatch):
    """Provide real tiny plugin trees in the server-contained download cache."""
    name, game, app = request.param
    adapter = import_module(f"gamemodules.{name}.workshop")
    shared = import_module("gamemodules.squadserver.workshop")
    server = DummyServer("squadworkshop")
    server.data["dir"] = str(tmp_path)
    payloads = {}
    for item in ("111", "222"):
        payload = tmp_path / ".alphagsm/fixtures" / item
        plugin = payload / "Example"
        (plugin / "Content/Paks/LinuxServer").mkdir(parents=True)
        (plugin / "Content/Paks/WindowsServer").mkdir(parents=True)
        (plugin / "Example.uplugin").write_text(json.dumps({"FileVersion": 3,
                                                          "CanContainContent": True}))
        (plugin / "Example.mi").write_text(f"[Modding.Core]\nName=Example\nID={item}\n")
        (plugin / "Content/Paks/LinuxServer/Example.pak").write_bytes(b"linux" + item.encode())
        (plugin / "Content/Paks/LinuxServer/Example.utoc").write_bytes(b"toc")
        (plugin / "Content/Paks/LinuxServer/Example.ucas").write_bytes(b"ucas")
        (plugin / "Content/Paks/WindowsServer/Example.pak").write_bytes(b"windows")
        payloads[item] = payload
    def download(_server, actual_app, ids):
        assert actual_app == app
        return {item: payloads[item] for item in ids}
    monkeypatch.setattr(shared, "download_workshop_items", download)
    return adapter, server, payloads, tmp_path / game / "Plugins/Mods"


def test_linux_plugin_stages_descriptor_pak_and_iostore_and_cleans_only_owned(plugin_server):
    adapter, server, _payloads, mods = plugin_server
    operator = mods / "Operator/keep.txt"
    operator.parent.mkdir(parents=True)
    operator.write_text("keep")
    adapter.configure_workshop(server, ["111"])
    assert (mods / "111/Example/Example.uplugin").is_file()
    assert (mods / "111/Example/Content/Paks/LinuxServer/Example.pak").read_bytes() == b"linux111"
    assert (mods / "111/Example/Content/Paks/LinuxServer/Example.utoc").is_file()
    assert not (mods / "111/Example/Content/Paks/WindowsServer/Example.pak").exists()
    adapter.configure_workshop(server, [])
    assert operator.read_text() == "keep"
    assert not (mods / "111/Example/Example.uplugin").exists()


def test_invalid_later_plugin_does_not_partially_publish(plugin_server):
    adapter, server, payloads, mods = plugin_server
    (payloads["222"] / "Example/Example.uplugin").write_text("{}")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111", "222"])
    assert not (mods / "111/Example/Example.uplugin").exists()


def test_existing_operator_plugin_and_owned_edits_are_preserved(plugin_server):
    adapter, server, _payloads, mods = plugin_server
    target = mods / "111/Example/Example.uplugin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"operator")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111"])
    assert target.read_bytes() == b"operator"
    target.unlink()
    adapter.configure_workshop(server, ["111"])
    target.write_bytes(b"edited")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, [])
    assert target.read_bytes() == b"edited"


def test_windows_only_plugin_rejected(plugin_server):
    adapter, server, payloads, _mods = plugin_server
    (payloads["111"] / "Example/Content/Paks/LinuxServer/Example.pak").unlink()
    with pytest.raises(ServerError, match="Linux"):
        adapter.configure_workshop(server, ["111"])


def test_mismatched_native_workshop_identity_rejected(plugin_server):
    adapter, server, payloads, _mods = plugin_server
    (payloads["111"] / "Example/Example.mi").write_text("[Modding.Core]\nID=999\n")
    with pytest.raises(ServerError, match="identity"):
        adapter.configure_workshop(server, ["111"])
