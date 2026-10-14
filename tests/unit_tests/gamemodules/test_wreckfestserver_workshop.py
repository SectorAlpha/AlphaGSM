"""Native Wreckfest activation, payload ownership and rollback contracts."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from gamemodules import wreckfestserver as module
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


def adapter():
    assert hasattr(module, "MOD_SUPPORT"), "Wreckfest needs native Workshop activation"
    from gamemodules.wreckfestserver import workshop
    return workshop


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setattr(module.runtime_module, "check_server_running", lambda _: False)
    return SimpleNamespace(name="wf", data=DummyData(dir=str(tmp_path), configfile="server_config.cfg"), module=module)


def payload(root):
    source = root / ".alphagsm/workshop/content/228380/123"
    source.mkdir(parents=True)
    (source / "modinfo.modi").write_bytes(b"\x04\0\0\0idom" + b"\0" * 20)
    (source / "data").mkdir()
    (source / "data/fixture.dset").write_bytes(b"native fixture")
    return source


def test_activation_and_cleanup_preserve_operator_configuration_and_files(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    config = tmp_path / "server_config.cfg"
    config.write_text("# operator comment\nserver_name=Mine\nmods=operator,456\nweather=rain\n")
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    assert "mods=operator,456,alphagsm-123\n" in config.read_text()
    assert "weather=rain\n" in config.read_text() and "# operator comment" in config.read_text()
    destination = tmp_path / "mods/alphagsm-123"
    assert (destination / "data/fixture.dset").read_bytes() == b"native fixture"
    (destination / "operator-extra.txt").write_text("keep")
    ws.apply_workshop(server, [])
    assert "mods=operator,456\n" in config.read_text()
    assert not (destination / "data/fixture.dset").exists()
    assert (destination / "operator-extra.txt").read_text() == "keep"
    assert source.exists()


def test_invalid_native_metadata_and_executable_payload_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    (source / "modinfo.modi").write_bytes(b"not native")
    with pytest.raises(ServerError, match="modinfo"):
        ws.apply_workshop(server, ["123"])
    (source / "modinfo.modi").write_bytes(b"\x04\0\0\0idom" + b"\0" * 20)
    (source / "plugin.exe").write_bytes(b"arbitrary executable")
    with pytest.raises(ServerError, match="executable"):
        ws.apply_workshop(server, ["123"])
    assert not (tmp_path / "server_config.cfg").exists()


def test_symlink_payload_and_config_escape_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    (source / "data/fixture.dset").unlink()
    (source / "data/fixture.dset").symlink_to(source / "modinfo.modi")
    with pytest.raises(ServerError, match="symlink"):
        ws.apply_workshop(server, ["123"])
    server.data["configfile"] = "../escape.cfg"
    with pytest.raises(ServerError):
        ws.apply_workshop(server, [])


def test_unowned_native_name_and_duplicate_mods_keys_are_refused(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    config = tmp_path / "server_config.cfg"
    config.write_text("mods=alphagsm-123\n")
    with pytest.raises(ServerError, match="owned"):
        ws.apply_workshop(server, ["123"])
    config.write_text("mods=operator\nmods=other\n")
    with pytest.raises(ServerError, match="duplicate"):
        ws.apply_workshop(server, ["123"])


def test_edited_owned_payload_causes_config_and_metadata_rollback(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    config = tmp_path / "server_config.cfg"
    original = config.read_text()
    before = dict(server.data["wreckfest_workshop"])
    (tmp_path / "mods/alphagsm-123/data/fixture.dset").write_text("operator edit")
    with pytest.raises(ServerError):
        ws.apply_workshop(server, [])
    assert config.read_text() == original
    assert server.data["wreckfest_workshop"] == before


def test_owned_config_tracks_before_publisher_save(server, tmp_path, monkeypatch):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    real = ws.owned_payloads.publish_owned_payloads
    def observe(current, owner, files):
        assert current.data["wreckfest_workshop"]["folders"] == ["alphagsm-123"]
        return real(current, owner, files)
    monkeypatch.setattr(ws.owned_payloads, "publish_owned_payloads", observe)
    ws.apply_workshop(server, ["123"])


def test_lifecycle_respects_autoapply_false(server, tmp_path, monkeypatch):
    adapter()
    server.data["mods"] = {"enabled": True, "autoapply": False, "desired": {"workshop": []}}
    calls = []
    monkeypatch.setattr(module.MOD_SUPPORT, "apply_configured_mods", lambda _: calls.append(True))
    monkeypatch.setattr(module, "sync_server_config", lambda _: None)
    module.prestart(server)
    module.apply_automatic_mods(server)
    assert not calls


def test_track_setting_requires_installed_native_event_and_syncs_config(server, tmp_path):
    event = tmp_path / "mods/operator/data/property/event/custom/custom_course.evse"
    event.parent.mkdir(parents=True)
    event.write_bytes(b"native event fixture")
    assert module.checkvalue(server, ("track",), "custom_course") == "custom_course"
    for invalid in ("../custom_course", "missing_course"):
        with pytest.raises(ServerError):
            module.checkvalue(server, ("track",), invalid)
    server.data.update(track="custom_course", port=33540, queryport=27016, steamport=27015)
    module.sync_server_config(server)
    assert "track=custom_course" in (tmp_path / "server_config.cfg").read_text()
    assert "track" in module.config_sync_keys


def test_explicit_wineprefix_keeps_validation_assets_under_server_root(server, tmp_path):
    prefix = str(tmp_path / ".alphagsm-wineprefix")
    assert module.checkvalue(server, ("wineprefix",), prefix) == prefix
    assert "wineprefix" not in module.config_sync_keys


def test_lifecycle_refuses_symlink_config_before_sync_changes_operator_file(server, tmp_path):
    original = tmp_path / "operator.cfg"
    original.write_text("server_name=Keep\n")
    (tmp_path / "server_config.cfg").symlink_to(original)
    server.data["servername"] = "Changed"
    with pytest.raises(ServerError, match="symlink"):
        module.prestart(server)
    assert original.read_text() == "server_name=Keep\n"


def test_linux_console_inherits_cmd_console_and_refuses_shell_metacharacters(server, tmp_path, monkeypatch):
    (tmp_path / "Wreckfest_x64.exe").write_bytes(b"fixture exe")
    server.data["exe_name"] = "Wreckfest_x64.exe"
    monkeypatch.setattr(module, "IS_LINUX", True)
    monkeypatch.setattr(module.proton, "wrap_command", lambda command, **_: command)
    command, directory = module.get_start_command(server)
    assert command[-5:-2] == ["cmd.exe", "/c", "Wreckfest_x64.exe"]
    assert directory == str(tmp_path)
    server.data["configfile"] = "config&other.cfg"
    with pytest.raises(ServerError, match="console"):
        module.get_start_command(server)


def test_linux_process_has_same_xvfb_drivers_as_docker(server, tmp_path, monkeypatch):
    (tmp_path / "Wreckfest_x64.exe").write_bytes(b"fixture exe")
    server.data["exe_name"] = "Wreckfest_x64.exe"
    monkeypatch.setattr(module, "IS_LINUX", True)
    monkeypatch.setattr(module.proton, "wrap_command", lambda command, **_: [
        "env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "wine", *command])
    command, _ = module.get_start_command(server)
    assert command[:2] == ["xvfb-run", "-a"]
    assert "WINEDLLOVERRIDES=winex11.drv=" not in command
    assert "DISPLAY=" not in command
    assert "SDL_VIDEODRIVER=x11" in command
    assert "WINEDLLOVERRIDES=" in command


def test_native_container_command_resolves_windows_builtin_cmd(server, tmp_path, monkeypatch):
    (tmp_path / "Wreckfest_x64.exe").write_bytes(b"fixture exe")
    server.data.update(exe_name="Wreckfest_x64.exe", port=33540, queryport=27016, steamport=27015)
    monkeypatch.setattr(module, "IS_LINUX", True)
    monkeypatch.setattr(module.proton, "wrap_command", lambda command, **_: ["wine", *command])
    spec = module.get_container_spec(server)
    assert spec["command"] == [
        "cmd.exe", "/c", "Wreckfest_x64.exe", "-s", "server_config=server_config.cfg",
    ]
    assert spec["working_dir"] == "/srv/server"


@pytest.mark.parametrize("desired", [["456"], []])
def test_running_server_refuses_apply_and_cleanup_before_download_or_publication(server, tmp_path, monkeypatch, desired):
    ws = adapter()
    source = payload(tmp_path)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: {"123": source})
    ws.apply_workshop(server, ["123"])
    before_files = {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    before_state, before_saves = deepcopy(server.data), server.data.saved
    monkeypatch.setattr(module.runtime_module, "check_server_running", lambda _: True)
    monkeypatch.setattr(ws, "download_workshop_items", lambda *_: pytest.fail("Running guard must precede download"))
    monkeypatch.setattr(ws.owned_payloads, "publish_owned_payloads", lambda *_: pytest.fail("Running guard must precede payload publication"))
    with pytest.raises(ServerError, match="Stop.*running"):
        ws.apply_workshop(server, desired)
    assert {path.relative_to(tmp_path): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()} == before_files
    assert server.data == before_state and server.data.saved == before_saves
