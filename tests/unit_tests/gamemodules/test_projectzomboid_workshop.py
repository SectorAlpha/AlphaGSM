"""Project Zomboid native Workshop ID discovery and activation regressions."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from gamemodules import projectzomboid as module
from tests.unit_tests.gamemodules.helpers import DummyData
from server import ServerError


def _payload(tmp_path, item, folder, text, version=None):
    root = tmp_path / ".alphagsm" / "workshop" / "content" / "108600" / item
    mod_root = root / "mods" / folder
    info = mod_root / version / "mod.info" if version else mod_root / "mod.info"
    info.parent.mkdir(parents=True, exist_ok=True)
    info.write_text(text, encoding="utf-8")
    (info.parent / "media").mkdir(exist_ok=True)
    return root


def _server(tmp_path):
    return SimpleNamespace(name="pz", data=DummyData(dir=str(tmp_path), servername="pz",
                          port=16261, queryport=16262), module=module)


def test_native_workshop_command_is_exposed():
    assert "mod" in module.commands
    assert module.workshop_app_id == 108600


def test_mod_ids_are_discovered_and_dependencies_precede_dependants(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    one = _payload(tmp_path, "1", "Feature", "id=Feature\nrequire=Library\n")
    two = _payload(tmp_path, "2", "Library", "id=Library\n")
    assert support.inspect_workshop_mods({"1": one, "2": two}, (41, 78, 16)) == ["Library", "Feature"]


@pytest.mark.parametrize("text,match", [
    ("name=Missing ID\n", "id"), ("id=../outside\n", "id"),
    ("id=Bad;Injected\n", "id"), ("id=Feature\nrequire=Missing\n", "dependency"),
])
def test_invalid_or_unsatisfied_mod_metadata_is_rejected(tmp_path, text, match):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", text)
    with pytest.raises(ServerError, match=match):
        support.inspect_workshop_mods({"1": payload}, (41, 78, 16))


def test_build_42_selects_matching_version_and_ignores_legacy(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", "id=Legacy\n")
    _payload(tmp_path, "1", "Feature", "id=Modern\n", "42.13")
    _payload(tmp_path, "1", "Feature", "id=Future\n", "42.22")
    assert support.inspect_workshop_mods({"1": payload}, (42, 21, 0)) == ["\\Modern"]


def test_build_42_cannot_activate_legacy_only_mod(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", "id=Legacy\n")
    with pytest.raises(ServerError, match="compatible"):
        support.inspect_workshop_mods({"1": payload}, (42, 21, 0))


def test_duplicate_mod_ids_are_rejected(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    one = _payload(tmp_path, "1", "Feature", "id=Duplicate\n")
    two = _payload(tmp_path, "2", "Library", "id=Duplicate\n")
    with pytest.raises(ServerError, match="Duplicate"):
        support.inspect_workshop_mods({"1": one, "2": two}, (41, 78, 16))


def test_map_mods_require_explicit_map_order(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", "id=MapFeature\n")
    (payload / "mods" / "Feature" / "media" / "maps").mkdir()
    with pytest.raises(ServerError, match="map"):
        support.inspect_workshop_mods({"1": payload}, (41, 78, 16))


def test_apply_preserves_operator_entries_and_cleanup_removes_only_owned_entries(tmp_path, monkeypatch):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\n")
    monkeypatch.setattr(support, "download_workshop_items", lambda *_: {"1": payload})
    monkeypatch.setattr(support, "installed_game_version", lambda *_: (41, 78, 16))
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    original = "# operator comment\nWorkshopItems=99\nMods=LocalOperator\nMap=Muldraugh, KY\nCustom=keep\n"
    config.write_text(original)
    support.apply_workshop_mods(server, ["1"])
    assert "WorkshopItems=99;1" in config.read_text()
    assert "Mods=LocalOperator;Feature" in config.read_text()
    assert "Custom=keep" in config.read_text()
    support.apply_workshop_mods(server, [])
    assert config.read_text() == original


def test_failed_metadata_leaves_config_unchanged(tmp_path, monkeypatch):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\nrequire=Missing\n")
    monkeypatch.setattr(support, "download_workshop_items", lambda *_: {"1": payload})
    monkeypatch.setattr(support, "installed_game_version", lambda *_: (41, 78, 16))
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    config.write_text("Mods=Operator\nWorkshopItems=99\n")
    with pytest.raises(ServerError, match="dependency"):
        support.apply_workshop_mods(server, ["1"])
    assert config.read_text() == "Mods=Operator\nWorkshopItems=99\n"


def test_symlinked_metadata_and_config_are_rejected(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\n")
    info = payload / "mods" / "Feature" / "mod.info"
    real = tmp_path / "outside.info"
    info.rename(real)
    info.symlink_to(real)
    with pytest.raises(ServerError, match="symlink"):
        support.inspect_workshop_mods({"1": payload}, (41, 78, 16))
    (tmp_path / "Zomboid").symlink_to(tmp_path.parent)
    with pytest.raises(ServerError, match="symlink|outside|contain"):
        support.apply_workshop_mods(_server(tmp_path), [])


def test_installed_build_comes_from_engine_constant(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    core = tmp_path / "zombie" / "core" / "Core.class"
    core.parent.mkdir(parents=True)
    core.write_bytes(b"\xca\xfe\xba\xbe\x01\x00\x0841.78.16\x00")
    assert support.installed_game_version(_server(tmp_path)) == (41, 78, 16)
    core.write_bytes(b"\xca\xfe\xba\xbe\x01\x00\x0841.78.16\x00\x01\x00\x0742.21.0\x00")
    with pytest.raises(ServerError, match="unambiguously"):
        support.installed_game_version(_server(tmp_path))


@pytest.mark.parametrize("text,version,match", [
    ("id=Feature\nversionMin=42.22.0\n", (42, 21, 0), "compatible"),
    ("id=Feature\nrequire=Feature\n", (41, 78, 16), "Cyclic"),
    ("id=Feature\nid=Other\n", (41, 78, 16), "Duplicate"),
])
def test_version_ranges_cycles_and_duplicate_metadata(tmp_path, text, version, match):
    from gamemodules.projectzomboid import workshop as support
    payload = _payload(tmp_path, "1", "Feature", text, "42" if version[0] == 42 else None)
    with pytest.raises(ServerError, match=match):
        support.inspect_workshop_mods({"1": payload}, version)


def test_native_ports_sync_preserves_other_keys_and_command_cache_is_portable(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    config.write_text("DefaultPort=1\nUDPPort=2\nMods=Operator\nPublicName=Keep\n")
    support.sync_server_config(server)
    assert config.read_text() == "DefaultPort=16261\nUDPPort=16262\nMods=Operator\nPublicName=Keep\n"
    (tmp_path / "start-server.sh").write_text("")
    server.data.update(exe_name="start-server.sh", adminpassword="secret")
    command, _ = module.get_start_command(server)
    assert "-cachedir=./Zomboid" in command
    container = module.get_container_spec(server)
    assert "-cachedir=./Zomboid" in container["command"]
    assert module.config_sync_keys == ("port", "queryport", "servername")


def test_cleanup_does_not_claim_preexisting_identical_entries(tmp_path, monkeypatch):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\n")
    monkeypatch.setattr(support, "download_workshop_items", lambda *_: {"1": payload})
    monkeypatch.setattr(support, "installed_game_version", lambda *_: (41, 78, 16))
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    config.write_text("Mods=Feature\nWorkshopItems=1\n")
    support.apply_workshop_mods(server, ["1"])
    support.apply_workshop_mods(server, [])
    assert config.read_text() == "Mods=Feature\nWorkshopItems=1\n"


def test_installed_build_reads_current_server_jar(tmp_path):
    from zipfile import ZipFile
    from gamemodules.projectzomboid import workshop as support
    jar = tmp_path / "java" / "projectzomboid.jar"
    jar.parent.mkdir()
    with ZipFile(jar, "w") as archive:
        archive.writestr("zombie/core/Core.class", b"\xca\xfe\xba\xbe\x01\x00\x0742.21.0\x00")
    assert support.installed_game_version(_server(tmp_path)) == (42, 21, 0)


def test_build_42_version_uses_actual_game_version_field(tmp_path):
    """Modern builds construct GameVersion from integers in the static initializer."""
    from zipfile import ZipFile
    from struct import pack
    from gamemodules.projectzomboid import workshop as support
    def utf8(value):
        raw = value.encode()
        return b"\x01" + pack(">H", len(raw)) + raw
    constants = [utf8("zombie/core/GameVersion"), b"\x07\x00\x01",
                 utf8("<init>"), utf8("(IILjava/lang/String;)V"),
                 b"\x0c\x00\x03\x00\x04", b"\x0a\x00\x02\x00\x05",
                 utf8("zombie/core/Core"), b"\x07\x00\x07",
                 utf8("gameVersion"), utf8("Lzombie/core/GameVersion;"),
                 b"\x0c\x00\x09\x00\x0a", b"\x09\x00\x08\x00\x0b",
                 utf8("0"), b"\x08\x00\x0d", utf8("41.78.16")]
    # Constructor arguments 42,21,"0", then writes Core.gameVersion.
    code = b"\xbb\x00\x02\x59\x10\x2a\x10\x15\x12\x0e\xb7\x00\x06\xb3\x00\x0c"
    jar = tmp_path / "java" / "projectzomboid.jar"
    jar.parent.mkdir()
    with ZipFile(jar, "w") as archive:
        archive.writestr("zombie/core/Core.class", b"\xca\xfe\xba\xbe\x00\x00\x00\x41" + pack(">H", 16) + b"".join(constants) + code)
    assert support.installed_game_version(_server(tmp_path)) == (42, 21, 0)


def test_load_verification_requires_engine_install_and_lua_execution():
    from tests.smoke_tests.projectzomboid_workshop import assert_workshop_loaded
    native = "Workshop: item state CheckItemState -> Ready ID=2773478544\nloading PrintIngameTimeOneHour\n"
    executed = "Date in game (dd/mm/yyyy) - 09/07/1993 09:00\n"
    assert_workshop_loaded(native + executed)
    with pytest.raises(AssertionError, match="Lua"):
        assert_workshop_loaded(native)
    with pytest.raises(AssertionError, match="engine"):
        assert_workshop_loaded(executed)
    with pytest.raises(AssertionError, match="Mod ID"):
        assert_workshop_loaded(native + executed + 'required mod "PrintIngameTimeOneHour" not found')


def test_servername_rejects_path_escape_before_set(tmp_path):
    server = _server(tmp_path)
    with pytest.raises(ServerError, match="servername"):
        module.checkvalue(server, ("servername",), "../../outside")


def test_dependency_ids_can_reference_another_workshop_package(tmp_path):
    from gamemodules.projectzomboid import workshop as support
    first = _payload(tmp_path, "1", "Feature", "id=1/Feature\nrequire=2/Library\n", "42")
    second = _payload(tmp_path, "2", "Library", "id=2/Library\n", "42")
    assert support.inspect_workshop_mods({"1": first, "2": second}, (42, 21, 0)) == ["\\2/Library", "\\1/Feature"]


def test_prestart_respects_native_autoapply_switch(tmp_path, monkeypatch):
    server = _server(tmp_path)
    server.data["mods"] = {"enabled": True, "autoapply": False}
    called = []
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda *_: called.append(True))
    module.prestart(server)
    assert called == []


@pytest.mark.parametrize("hook", ["install", "update"])
@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("autoapply", [True, False])
def test_download_hooks_respect_autoapply_for_native_activation(tmp_path, monkeypatch, hook, enabled, autoapply):
    from tests.unit_tests.gamemodules.helpers import DummyServer
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=16261, servername="pz",
                       mods={"enabled": enabled, "autoapply": autoapply})
    server.data["projectzomboid_workshop"] = {
        "profile": "Zomboid/Server/pz.ini", "Mods": ["Managed"], "WorkshopItems": ["1"]
    }
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    config.write_text("Mods=Managed;Operator\nWorkshopItems=1;99\nCustom=keep\n")
    monkeypatch.setattr(module.steamcmd, "download", lambda *_args, **_kwargs: None)
    getattr(module, hook)(server)
    expected = ("Mods=Operator\nWorkshopItems=99\nCustom=keep\n" if autoapply else
                "Mods=Managed;Operator\nWorkshopItems=1;99\nCustom=keep\n")
    assert expected in config.read_text()
    assert server.data["projectzomboid_workshop"]["Mods"] == ([] if autoapply else ["Managed"])


def test_disabling_native_mods_removes_owned_activation_and_keeps_desired(tmp_path, monkeypatch):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\n")
    monkeypatch.setattr(support, "download_workshop_items", lambda *_: {"1": payload})
    monkeypatch.setattr(support, "installed_game_version", lambda *_: (41, 78, 16))
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    config.write_text("Mods=Operator\nWorkshopItems=99\n")
    support.apply_workshop_mods(server, ["1"])
    server.data["mods"] = {"enabled": False, "autoapply": True,
                           "desired": {"workshop": [{"workshop_id": "1"}]}}
    module.prestart(server)
    assert "Mods=Operator\n" in config.read_text()
    assert "WorkshopItems=99\n" in config.read_text()
    assert server.data["mods"]["desired"]["workshop"] == [{"workshop_id": "1"}]


@pytest.mark.parametrize("operation", ["apply", "sync"])
def test_generated_ini_limit_preserves_operator_config_and_ownership(tmp_path, monkeypatch, operation):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    payload = _payload(tmp_path, "1", "Feature", "id=Feature\n")
    monkeypatch.setattr(support, "download_workshop_items", lambda *_: {"1": payload})
    monkeypatch.setattr(support, "installed_game_version", lambda *_: (41, 78, 16))
    previous = {"profile": "Zomboid/Server/pz.ini", "Mods": [], "WorkshopItems": []}
    server.data["projectzomboid_workshop"] = previous.copy()
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    suffix = "\nMods=\nWorkshopItems=\nDefaultPort=1\nUDPPort=2\n"
    original = "Custom=" + "x" * (1024 * 1024 - len(suffix) - len("Custom=") - 1) + suffix
    config.write_text(original, encoding="utf-8")
    with pytest.raises(ServerError, match="size limit"):
        if operation == "apply":
            support.apply_workshop_mods(server, ["1"])
        else:
            support.sync_server_config(server)
    assert config.read_text(encoding="utf-8") == original
    assert server.data["projectzomboid_workshop"] == previous


@pytest.mark.parametrize("operation", ["apply", "sync"])
def test_ini_read_limit_counts_utf8_bytes_without_changing_operator_config(tmp_path, operation):
    from gamemodules.projectzomboid import workshop as support
    server = _server(tmp_path)
    config = tmp_path / "Zomboid" / "Server" / "pz.ini"
    config.parent.mkdir(parents=True)
    original = "Custom=" + "\u00e9" * 600000 + "\nMods=\nWorkshopItems=\n"
    assert len(original) < 1024 * 1024 < len(original.encode("utf-8"))
    config.write_text(original, encoding="utf-8")
    with pytest.raises(ServerError, match="size limit"):
        if operation == "apply":
            support.apply_workshop_mods(server, [])
        else:
            support.sync_server_config(server)
    assert config.read_text(encoding="utf-8") == original
    assert "projectzomboid_workshop" not in server.data
