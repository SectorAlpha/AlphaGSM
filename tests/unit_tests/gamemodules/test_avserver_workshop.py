"""Avorion managed Lua block, metadata and native lifecycle regressions."""
from types import SimpleNamespace

import pytest

from gamemodules import avserver as module
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(name="avfixture", data=DummyData(dir=str(tmp_path), galaxy="fixture"), module=module)


def adapter():
    assert hasattr(module, "MOD_SUPPORT"), "Avorion must expose validated native Workshop activation"
    from gamemodules.avserver import workshop
    return workshop


def payload(root, item, *, dependencies="{}", client="false", suffix=""):
    source = root / ".alphagsm/workshop/content/445220" / item
    source.mkdir(parents=True)
    (source / "modinfo.lua").write_text(
        'meta={id="' + item + '",name="Mod' + item + '",type="mod",version="1.0",'
        'clientSideOnly=' + client + ',dependencies=' + dependencies + '}' + suffix
    )
    return source


def test_preserves_operator_lua_and_removes_only_owned_block(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path, "123")
    config = tmp_path / "galaxies/fixture/modconfig.lua"
    config.parent.mkdir(parents=True)
    original = '-- operator\nmodLocation=""\nforceEnabling=false\nmods={{workshopid="999"}}\nallowed={}\n'
    config.write_text(original)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    assert config.read_text().startswith(original)
    assert 'workshopid = "123"' in config.read_text()
    ws.apply_workshop(server, [])
    assert config.read_text() == original
    assert source.exists()


def test_dependency_is_required_and_is_enabled_first(server, tmp_path, monkeypatch):
    ws = adapter()
    child = payload(tmp_path, "123", dependencies='{{id="456",min="1.0"}}')
    base = payload(tmp_path, "456")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": child, "456": base})
    with pytest.raises(ServerError, match="dependency"):
        ws.apply_workshop(server, ["123"])
    ws.apply_workshop(server, ["123", "456"])
    text = (tmp_path / "galaxies/fixture/modconfig.lua").read_text()
    assert text.index('workshopid = "456"') < text.index('workshopid = "123"')


@pytest.mark.parametrize("client,suffix", [("true", ""), ("false", ';os.execute("touch bad")')])
def test_client_only_or_executable_metadata_is_refused(server, tmp_path, monkeypatch, client, suffix):
    ws = adapter()
    source = payload(tmp_path, "123", client=client, suffix=suffix)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    with pytest.raises(ServerError):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "galaxies/fixture/modconfig.lua").exists()


def test_native_entry_external_edit_is_preserved(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path, "123")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    config = tmp_path / "galaxies/fixture/modconfig.lua"
    changed = config.read_text().replace('workshopid = "123"', 'workshopid = "456"')
    config.write_text(changed)
    with pytest.raises(ServerError, match="changed"):
        ws.apply_workshop(server, [])
    assert config.read_text() == changed


def test_unsafe_galaxy_and_symlink_metadata_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path, "123")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    server.data["galaxy"] = "../escape"
    with pytest.raises(ServerError):
        ws.apply_workshop(server, ["123"])
    server.data["galaxy"] = "fixture"
    metadata = source / "modinfo.lua"
    target = source / "original.lua"
    metadata.rename(target)
    metadata.symlink_to(target)
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, ["123"])


def test_prestart_respects_autoapply_false(server, monkeypatch):
    adapter()
    server.data["mods"] = {"autoapply": False}
    calls = []
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda _: calls.append(True))
    module.prestart(server)
    assert not calls


def test_graceful_stop_uses_native_slash_command(server, monkeypatch):
    calls = []
    monkeypatch.setattr(module.runtime_module, "send_to_server", lambda _, text: calls.append(text))
    module.do_stop(server, 0)
    assert calls == ["\n/stop\n"]


def test_wrong_native_id_and_dependency_cycle_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    one = payload(tmp_path, "123", dependencies='{{id="456"}}')
    two = payload(tmp_path, "456", dependencies='{{id="123"}}')
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": one, "456": two})
    with pytest.raises(ServerError, match="cycle"):
        ws.apply_workshop(server, ["123", "456"])
    (one / "modinfo.lua").write_text('meta={id="999",name="Mismatch",type="mod"}')
    with pytest.raises(ServerError, match="identity"):
        ws.apply_workshop(server, ["123"])


def test_dependency_version_requirement_is_checked(server, tmp_path, monkeypatch):
    ws = adapter()
    one = payload(tmp_path, "123", dependencies='{{id="456",min="2.0"}}')
    two = payload(tmp_path, "456")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": one, "456": two})
    with pytest.raises(ServerError, match="version"):
        ws.apply_workshop(server, ["123", "456"])


def test_cleanup_after_galaxy_change_removes_old_owned_block(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path, "123")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    server.data["galaxy"] = "different"
    ws.apply_workshop(server, [])
    assert "123" not in (tmp_path / "galaxies/fixture/modconfig.lua").read_text()
    assert not (tmp_path / "galaxies/different/modconfig.lua").exists()
