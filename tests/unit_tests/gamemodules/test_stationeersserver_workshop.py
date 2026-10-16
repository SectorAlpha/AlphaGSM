"""Native Stationeers XML mods and operator ownership regressions."""

from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from gamemodules import stationeersserver as module
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


def adapter():
    assert hasattr(module, "MOD_SUPPORT"), "Stationeers needs native XML Workshop activation"
    from gamemodules.stationeersserver import workshop
    return workshop


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(name="st", data=DummyData(dir=str(tmp_path)), module=module)


def payload(root, item="123", name="Stack Fixture"):
    source = root / ".alphagsm/workshop/content/544550" / item
    (source / "About").mkdir(parents=True)
    (source / "GameData").mkdir()
    (source / "About/About.xml").write_text(
        f'<ModMetadata><Name>{name}</Name><WorkshopHandle>{item}</WorkshopHandle></ModMetadata>')
    (source / "GameData/stack.xml").write_text(
        '<GameData><ThingMods><ThingMod><PrefabName>ItemIronOre</PrefabName>'
        '<Stackable><MaxQuantity>500</MaxQuantity></Stackable></ThingMod></ThingMods></GameData>')
    return source


def test_native_config_and_cleanup_preserve_operator_mod_order_and_settings(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    config = tmp_path / "modconfig.xml"
    config.write_text('<ModConfig><!-- operator --><Local Enabled="true"><Path Value="mods/operator"/></Local>'
                      '<Core Enabled="true"/></ModConfig>')
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    root = ET.parse(config).getroot()
    entries = [(node.tag, node.get("Enabled"), node.find("Path").get("Value") if node.find("Path") is not None else None)
               for node in root if isinstance(node.tag, str)]
    assert entries == [("Local", "true", str(tmp_path / "mods/alphagsm-123")),
                       ("Local", "true", "mods/operator"), ("Core", "true", None)]
    assert "operator" in config.read_text()
    assert (tmp_path / "mods/alphagsm-123/GameData/stack.xml").exists()
    ws.apply_workshop(server, [])
    assert "alphagsm-123" not in config.read_text()
    assert "mods/operator" in config.read_text()
    assert not (tmp_path / "mods/alphagsm-123/GameData/stack.xml").exists()


def test_container_native_path_uses_the_mounted_root(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    monkeypatch.setattr(ws.runtime_module, "resolve_runtime_metadata", lambda _: {"runtime": "docker"})
    ws.apply_workshop(server, ["123"])
    document = ET.parse(tmp_path / "modconfig.xml").getroot()
    assert document.find("Local/Path").get("Value") == "/srv/server/mods/alphagsm-123"


def test_missing_or_wrong_about_identity_and_code_mods_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    (source / "About/About.xml").write_text('<ModMetadata><Name>Wrong</Name><WorkshopHandle>999</WorkshopHandle></ModMetadata>')
    with pytest.raises(ServerError, match="identity"):
        ws.apply_workshop(server, ["123"])
    (source / "About/About.xml").write_text('<ModMetadata><Name>Good</Name><WorkshopHandle>123</WorkshopHandle></ModMetadata>')
    (source / "plugin.dll").write_bytes(b"code")
    with pytest.raises(ServerError, match="code"):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "modconfig.xml").exists()


def test_symlink_payload_and_native_config_refused_before_changes(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    (source / "GameData/stack.xml").unlink()
    (source / "GameData/stack.xml").symlink_to(source / "About/About.xml")
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, ["123"])
    config = tmp_path / "operator.xml"
    config.write_text('<ModConfig/>')
    (tmp_path / "modconfig.xml").symlink_to(config)
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, [])


def test_external_entry_change_is_preserved(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    config = tmp_path / "modconfig.xml"
    changed = config.read_text().replace('Enabled="true"', 'Enabled="false"', 1)
    config.write_text(changed)
    with pytest.raises(ServerError, match="externally"):
        ws.apply_workshop(server, [])
    assert config.read_text() == changed


def test_xml_entity_and_asset_escape_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    for xml in ('<!DOCTYPE GameData [<!ENTITY x "oops">]><GameData/>',
                '<GameData><WorldSettings><World><FilePath>../../operator.xml</FilePath></World></WorldSettings></GameData>'):
        (source / "GameData/stack.xml").write_text(xml)
        with pytest.raises(ServerError):
            ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "modconfig.xml").exists()


def test_payload_refusal_restores_native_config_and_metadata(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    original = (tmp_path / "modconfig.xml").read_text()
    metadata = list(server.data["stationeers_workshop"])
    (tmp_path / "mods/alphagsm-123/GameData/stack.xml").write_text("operator edit")
    with pytest.raises(ServerError):
        ws.apply_workshop(server, [])
    assert (tmp_path / "modconfig.xml").read_text() == original
    assert server.data["stationeers_workshop"] == metadata


def test_autoapply_false_does_not_touch_native_configuration(server, monkeypatch):
    adapter()
    server.data["mods"] = {"enabled": True, "autoapply": False, "desired": {"workshop": []}}
    calls = []
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda _: calls.append(True))
    module.prestart(server)
    module.apply_automatic_mods(server)
    assert not calls


def test_operator_child_added_to_owned_entry_is_preserved(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    config = tmp_path / "modconfig.xml"
    changed = config.read_text().replace('</Local>', '<OperatorNote>keep</OperatorNote></Local>')
    config.write_text(changed)
    with pytest.raises(ServerError, match="externally"):
        ws.apply_workshop(server, [])
    assert config.read_text() == changed


@pytest.mark.parametrize("value", ["http://outside.invalid/file.xml", "file:///tmp/file.xml", "%APPDATA%/outside.xml"])
def test_native_asset_path_refuses_remote_or_environment_expansion(server, tmp_path, monkeypatch, value):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    (source / "GameData/stack.xml").write_text(f'<GameData><Texture Path="{value}"/></GameData>')
    with pytest.raises(ServerError, match="path"):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "modconfig.xml").exists()


def test_load_proof_requires_native_world_construction_and_matching_save(tmp_path):
    import zipfile
    from tests.smoke_tests.stationeersserver_workshop import assert_workshop_loaded
    save = tmp_path / "fresh.save"
    log = "successfully loaded the 'Mars Abandoned Frontier' mod\nWorldSetting: AbandonedMars StartCondition: DefaultScenario\nStarted new game. Saving...\n"
    with zipfile.ZipFile(save, "w") as archive:
        archive.writestr("world_meta.xml", '<WorldMetaData><WorldName>AbandonedMars</WorldName></WorldMetaData>')
        archive.writestr("world.xml", '<WorldData><WorldSetting Id="AbandonedMars"/><AllThings>'
                         '<ThingSaveData><PrefabName>StructureFrameIron</PrefabName></ThingSaveData>'
                         '</AllThings></WorldData>')
    assert_workshop_loaded(log, save)
    with pytest.raises(AssertionError):
        assert_workshop_loaded("worldname=AbandonedMars", save)
    with zipfile.ZipFile(save, "w") as archive:
        archive.writestr("world_meta.xml", '<WorldMetaData><WorldName>Lunar</WorldName></WorldMetaData>')
        archive.writestr("world.xml", '<WorldData><WorldSetting Id="Lunar"/></WorldData>')
    with pytest.raises(AssertionError):
        assert_workshop_loaded(log, save)
