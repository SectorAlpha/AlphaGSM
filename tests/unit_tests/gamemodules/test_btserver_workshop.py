"""Native Barotrauma XML activation and ownership regressions."""
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from gamemodules import btserver as module
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


def package(root, item="123", *, name="Test Items", core="false", file="%ModDir%/items.xml"):
    directory = root / ".alphagsm" / "workshop" / "content" / "602960" / item
    directory.mkdir(parents=True)
    (directory / "filelist.xml").write_text(
        f'<contentpackage name="{name}" corepackage="{core}" steamworkshopid="{item}">'
        f'<Item file="{file}"/></contentpackage>'
    )
    (directory / "items.xml").write_text('<Items><Item identifier="fixtureitem"/></Items>')
    return directory


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(name="btfixture", data=DummyData(dir=str(tmp_path)), module=module)


def adapter():
    assert hasattr(module, "MOD_SUPPORT"), "Barotrauma must expose native Workshop activation"
    from gamemodules.btserver import workshop
    return workshop


def test_native_activation_keeps_operator_xml_and_uses_package_identity(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    config = tmp_path / "config_player.xml"
    config.write_text('<config language="French"><!-- operator note --><contentpackages>'
                      '<corepackage path="Content/ContentPackages/Vanilla.xml"/>'
                      '<regularpackages><package name="Operator" path="LocalMods/operator/filelist.xml"/>'
                      '</regularpackages></contentpackages><audio volume="0.4"/></config>')
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    root = ET.parse(config).getroot()
    assert root.get("language") == "French"
    assert root.find("audio").get("volume") == "0.4"
    entries = root.findall("./contentpackages/regularpackages/package")
    assert [(entry.get("name"), entry.get("path")) for entry in entries] == [
        ("Operator", "LocalMods/operator/filelist.xml"),
        ("Test Items", "LocalMods/alphagsm-123/filelist.xml"),
    ]
    assert "operator note" in config.read_text()
    assert (tmp_path / "LocalMods/alphagsm-123/items.xml").exists()
    ws.apply_workshop(server, [])
    assert [entry.get("name") for entry in ET.parse(config).findall("./contentpackages/regularpackages/package")] == ["Operator"]
    assert not (tmp_path / "LocalMods/alphagsm-123/items.xml").exists()
    assert source.exists(), "Managed download cache should survive native cleanup"


@pytest.mark.parametrize("core,file", [("true", "%ModDir%/items.xml"),
                                       ("false", "../../outside.xml"),
                                       ("false", "/tmp/outside.xml")])
def test_invalid_package_never_changes_native_config(server, tmp_path, monkeypatch, core, file):
    ws = adapter()
    source = package(tmp_path, core=core, file=file)
    config = tmp_path / "config_player.xml"
    config.write_text("<config/>")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    with pytest.raises(ServerError):
        ws.apply_workshop(server, ["123"])
    assert config.read_text() == "<config/>"
    assert not (tmp_path / "LocalMods/alphagsm-123").exists()


def test_metadata_id_and_duplicate_names_are_rejected_before_publishing(server, tmp_path, monkeypatch):
    ws = adapter()
    one, two = package(tmp_path), package(tmp_path, "456")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": one, "456": two})
    with pytest.raises(ServerError, match="name"):
        ws.apply_workshop(server, ["123", "456"])
    (one / "filelist.xml").write_text('<contentpackage name="Wrong" steamworkshopid="999"/>')
    with pytest.raises(ServerError, match="identity"):
        ws.apply_workshop(server, ["123"])


def test_symlink_payload_and_config_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    (source / "items.xml").unlink()
    (source / "items.xml").symlink_to(source / "filelist.xml")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, ["123"])
    (source / "items.xml").unlink()
    (source / "items.xml").write_text("<Items/>")
    external = tmp_path / "operator.xml"
    external.write_text("<config/>")
    (tmp_path / "config_player.xml").symlink_to(external)
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, ["123"])
    assert external.read_text() == "<config/>"


def test_external_native_entry_edit_is_not_removed(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    config = tmp_path / "config_player.xml"
    config.write_text(config.read_text().replace('name="Test Items"', 'name="Operator Edit"'))
    with pytest.raises(ServerError, match="changed|modified"):
        ws.apply_workshop(server, [])
    assert "Operator Edit" in config.read_text()
    assert (tmp_path / "LocalMods/alphagsm-123/items.xml").exists()


def test_autoapply_false_does_not_apply_on_prestart(server, monkeypatch):
    adapter()
    server.data["mods"] = {"autoapply": False}
    calls = []
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda _: calls.append(True))
    module.prestart(server)
    assert not calls


def test_publisher_failure_preserves_config_and_native_ownership(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    config = tmp_path / "config_player.xml"
    original = '<config language="Russian"/>'
    config.write_text(original)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    def fail(*_):
        raise ServerError("Cannot publish fixture")
    monkeypatch.setattr(ws.owned_payloads, "publish_owned_payloads", fail)
    with pytest.raises(ServerError, match="Cannot publish"):
        ws.apply_workshop(server, ["123"])
    assert config.read_text() == original
    assert "barotrauma_workshop" not in server.data


def test_changed_payload_and_operator_extras_survive_cleanup(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    owned = tmp_path / "LocalMods/alphagsm-123/items.xml"
    owned.write_text("<Items operator_edit='yes'/>")
    extra = owned.parent / "operator.txt"
    extra.write_text("operator notes")
    before = (tmp_path / "config_player.xml").read_text()
    with pytest.raises(ServerError, match="changed|modified"):
        ws.apply_workshop(server, [])
    assert owned.exists() and extra.exists()
    assert (tmp_path / "config_player.xml").read_text() == before


def test_config_write_failure_leaves_payload_unchanged(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    before = (tmp_path / "config_player.xml").read_text()
    def fail(*_):
        raise OSError("Config filesystem failure")
    monkeypatch.setattr(ws, "write_managed_text", fail)
    with pytest.raises(OSError):
        ws.apply_workshop(server, [])
    assert (tmp_path / "LocalMods/alphagsm-123/items.xml").exists()
    assert (tmp_path / "config_player.xml").read_text() == before


def test_docker_console_uses_tty_for_native_engine_commands(server, tmp_path):
    (tmp_path / "DedicatedServer").write_text("fixture binary")
    server.data.update(exe_name="DedicatedServer", port=27015, queryport=27016,
                       gamemode="Sandbox", runtime={"backend": "docker"})
    spec = module.get_container_spec(server)
    assert spec["tty"] is True, "Barotrauma rejects redirected console input without a TTY"
    assert spec["stdin_open"] is True
    assert spec["command"][:2] == ["python3", ".alphagsm/btserver_terminal.py"], (
        "The Docker FIFO must feed a terminal with cursor replies, not the game directly"
    )


def test_nested_asset_root_path_cannot_escape_package(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    (source / "items.xml").write_text('<Items path="../../operator"><Item identifier="fixtureitem"/></Items>')
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    with pytest.raises(ServerError, match="Unsafe"):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "config_player.xml").exists()


def test_payload_save_has_matching_native_ownership(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    snapshots = []
    import copy
    monkeypatch.setattr(server.data, "save", lambda: snapshots.append(copy.deepcopy(dict(server.data))))
    ws.apply_workshop(server, ["123"])
    published = [state for state in snapshots if state.get("mods", {}).get("owned_payloads", {}).get("btserver")]
    assert published
    assert all(state.get("barotrauma_workshop") for state in published)


def test_nested_asset_xml_cannot_reference_outside_server(server, tmp_path, monkeypatch):
    ws = adapter()
    source = package(tmp_path)
    (source / "items.xml").write_text('<Items><Item><Sprite texture="../../secret.png"/></Item></Items>')
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    with pytest.raises(ServerError, match="Unsafe"):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "LocalMods/alphagsm-123/items.xml").exists()
