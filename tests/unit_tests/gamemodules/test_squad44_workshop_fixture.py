"""Squad 44 fixture selection derives its exact native identity from staged files."""

import pytest

from tests.smoke_tests.squad44server_workshop import (
    staged_plugin_name, select_workshop_layer, configure_workshop_layer,
    assert_native_map_loaded, assert_workshop_map_info,
)


LAYER = "Ramelle_Offensive_01"
LOADED = (
    "LogWorld: Bringing World /Ramelle/Maps/Ramelle_Offensive_01.Ramelle_Offensive_01 up for play\n"
    "LogLoad: Took 2.50 seconds to LoadMap(/Ramelle/Maps/Ramelle_Offensive_01)\n"
)


def test_default_ramelle_layer_and_explicit_override_fixture():
    assert select_workshop_layer("2387944294") == LAYER
    assert select_workshop_layer("123", "Another Offensive 01") == "Another Offensive 01"
    with pytest.raises(AssertionError, match="explicit"):
        select_workshop_layer("123")


@pytest.mark.parametrize("layer", ["../Ramelle", "Ramelle\nStock", "Ramelle;quit", ""])
def test_layer_rejects_unsafe_or_empty_override(layer):
    with pytest.raises(AssertionError):
        select_workshop_layer("123", layer)


def test_disposable_rotation_selects_only_workshop_layer(tmp_path):
    config = tmp_path / "PostScriptum/ServerConfig"
    config.mkdir(parents=True)
    (config / "Server.cfg").write_text("ServerName=keep\n")
    (config / "MapRotation.cfg").write_text("Veghel Offensive Random 01\n")
    configure_workshop_layer(tmp_path, LAYER)
    assert (config / "MapRotation.cfg").read_text() == LAYER + "\n"
    assert (config / "Server.cfg").read_text() == "ServerName=keep\n"


def test_disposable_rotation_refuses_symlink(tmp_path):
    config = tmp_path / "PostScriptum/ServerConfig"
    config.mkdir(parents=True)
    outside = tmp_path / "outside.cfg"
    outside.write_text("keep")
    (config / "MapRotation.cfg").symlink_to(outside)
    with pytest.raises(AssertionError):
        configure_workshop_layer(tmp_path, LAYER)
    assert outside.read_text() == "keep"


def test_actual_custom_world_and_a2s_layer_are_required():
    assert_native_map_loaded(LOADED, LAYER)
    assert_workshop_map_info({"protocol": "a2s", "map": "Ramelle Offensive 01"}, LAYER)


@pytest.mark.parametrize("log", [
    "LogPakFile: Mounted Pak file Ramelle.pak\nLogModdingRuntimeModule: Serialized Ramelle",
    LOADED.replace("Ramelle_Offensive_01", "Veghel_Offensive_Random_01"),
    "LogLoad: Took 2.50 seconds to LoadMap(/Ramelle/Maps/Ramelle_Offensive_01)",
])
def test_mounting_registry_or_stock_world_does_not_prove_map_execution(log):
    with pytest.raises(AssertionError):
        assert_native_map_loaded(log, LAYER)


@pytest.mark.parametrize("info", [
    {"protocol": "tcp", "map": "Ramelle Offensive 01"},
    {"protocol": "a2s", "map": "Veghel Offensive Random 01"},
    {"protocol": "a2s", "map": "Ramelle Offensive 02"},
])
def test_query_must_report_actual_selected_layer(info):
    with pytest.raises(AssertionError):
        assert_workshop_map_info(info, LAYER)


def _plugin(root, *, identity="2387944294", engine="4.27.2.SQ44", name="ActualCookedPlugin"):
    plugin = root / "PostScriptum/Plugins/Mods/2387944294" / name
    plugin.mkdir(parents=True)
    (plugin / (name + ".uplugin")).write_text(
        '{"FileVersion":3,"CanContainContent":true}', encoding="utf-8")
    (plugin / (name + ".mi")).write_text(
        f"[Modding.Core]\nName={name}\nEngine={engine}\nID={identity}\n", encoding="utf-8")
    return plugin


def test_fixture_derives_descriptor_name_without_guessing_from_workshop_title(tmp_path):
    _plugin(tmp_path)
    assert staged_plugin_name(tmp_path, "2387944294") == "ActualCookedPlugin"
    assert staged_plugin_name(tmp_path, "https://steamcommunity.com/sharedfiles/filedetails/?id=2387944294") == "ActualCookedPlugin"


@pytest.mark.parametrize("identity,engine", [("2909251852", "4.27.2.SQ44"),
                                             ("2387944294", "4.27.2")])
def test_fixture_rejects_wrong_identity_or_obsolete_sdk(tmp_path, identity, engine):
    _plugin(tmp_path, identity=identity, engine=engine)
    with pytest.raises(AssertionError):
        staged_plugin_name(tmp_path, "2387944294")


def test_fixture_override_must_match_an_actual_staged_plugin(tmp_path):
    _plugin(tmp_path)
    assert staged_plugin_name(tmp_path, "2387944294", "ActualCookedPlugin") == "ActualCookedPlugin"
    with pytest.raises(AssertionError):
        staged_plugin_name(tmp_path, "2387944294", "Ramelle")


def test_fixture_rejects_symlinked_descriptor(tmp_path):
    plugin = _plugin(tmp_path)
    descriptor = plugin / "ActualCookedPlugin.uplugin"
    descriptor.unlink()
    descriptor.symlink_to(tmp_path / "outside.uplugin")
    with pytest.raises(AssertionError):
        staged_plugin_name(tmp_path, "2387944294")


def test_fixture_rejects_ambiguous_plugin_names(tmp_path):
    _plugin(tmp_path)
    _plugin(tmp_path, name="SecondPlugin")
    with pytest.raises(AssertionError):
        staged_plugin_name(tmp_path, "2387944294")
