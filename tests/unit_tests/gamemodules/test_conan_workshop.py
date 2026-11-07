"""Conan native Workshop ordering, publication and operator boundaries."""

from importlib import import_module

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def adapter_server(tmp_path, monkeypatch):
    """Use tiny payloads and real publication instead of a downloaded server."""
    adapter = import_module("gamemodules.conanexiles.workshop")
    server = DummyServer("conanworkshop")
    server.data["dir"] = str(tmp_path / "server")
    (tmp_path / "server").mkdir()
    payloads = {}
    for item in ("111", "222"):
        folder = tmp_path / "server/.alphagsm/fixtures" / item
        folder.mkdir(parents=True)
        (folder / "Example.pak").write_bytes(b"pak-" + item.encode())
        payloads[item] = folder
    monkeypatch.setattr(adapter, "download_workshop_items", lambda _server, app, ids: {
        item: payloads[item] for item in ids if app == 440900})
    return adapter, server, payloads


def test_ordered_modlist_preserves_operator_content_and_cleanup(tmp_path, monkeypatch):
    adapter, server, _payloads = adapter_server(tmp_path, monkeypatch)
    mods = tmp_path / "server/ConanSandbox/Mods"
    mods.mkdir(parents=True)
    (mods / "modlist.txt").write_text("*Operator.pak\n")
    (mods / "Operator.pak").write_bytes(b"operator")
    adapter.configure_workshop(server, ["222", "111"])
    assert (mods / "modlist.txt").read_text().splitlines() == [
        "*Operator.pak", "*222/Example.pak", "*111/Example.pak"]
    assert (mods / "222/Example.pak").read_bytes() == b"pak-222"
    adapter.configure_workshop(server, [])
    assert (mods / "modlist.txt").read_text() == "*Operator.pak\n"
    assert (mods / "Operator.pak").read_bytes() == b"operator"
    assert not (mods / "222/Example.pak").exists()


def test_collision_does_not_publish_any_new_mod_or_change_list(tmp_path, monkeypatch):
    adapter, server, _payloads = adapter_server(tmp_path, monkeypatch)
    mods = tmp_path / "server/ConanSandbox/Mods"
    (mods / "222").mkdir(parents=True)
    (mods / "222/Example.pak").write_bytes(b"unowned")
    (mods / "modlist.txt").write_text("*Operator.pak\n")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111", "222"])
    assert not (mods / "111/Example.pak").exists()
    assert (mods / "222/Example.pak").read_bytes() == b"unowned"
    assert (mods / "modlist.txt").read_text() == "*Operator.pak\n"


def test_invalid_payload_and_symlink_are_rejected_before_activation(tmp_path, monkeypatch):
    adapter, server, payloads = adapter_server(tmp_path, monkeypatch)
    (payloads["222"] / "Example.pak").unlink()
    (payloads["222"] / "Example.pak").symlink_to(payloads["111"] / "Example.pak")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, ["111", "222"])
    assert not (tmp_path / "server/ConanSandbox/Mods/modlist.txt").exists()


def test_operator_edits_to_managed_pak_block_cleanup(tmp_path, monkeypatch):
    adapter, server, _payloads = adapter_server(tmp_path, monkeypatch)
    adapter.configure_workshop(server, ["111"])
    pak = tmp_path / "server/ConanSandbox/Mods/111/Example.pak"
    pak.write_bytes(b"edited")
    with pytest.raises(ServerError):
        adapter.configure_workshop(server, [])
    assert pak.read_bytes() == b"edited"
    assert "*111/Example.pak" in (pak.parents[1] / "modlist.txt").read_text()


def test_publication_failure_restores_previous_activation_and_ownership(tmp_path, monkeypatch):
    adapter, server, _payloads = adapter_server(tmp_path, monkeypatch)
    adapter.configure_workshop(server, ["111"])
    previous = list(server.data["mods"]["conan_workshop_lines"])
    def fail(*_args):
        raise OSError("disk full")
    monkeypatch.setattr(adapter, "publish_owned_payloads", fail)
    with pytest.raises(OSError, match="disk full"):
        adapter.configure_workshop(server, ["222"])
    assert server.data["mods"]["conan_workshop_lines"] == previous
    mods = tmp_path / "server/ConanSandbox/Mods"
    assert (mods / "modlist.txt").read_text() == "*111/Example.pak\n"
    assert (mods / "111/Example.pak").read_bytes() == b"pak-111"
