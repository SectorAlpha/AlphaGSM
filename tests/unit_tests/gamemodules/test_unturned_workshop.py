"""Unturned native Workshop activation and scoped configuration ownership."""

import json
from unittest.mock import patch

import pytest

import gamemodules.unturned as mod
from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def make_server(tmp_path):
    """Create only manager state; no downloaded server payload is needed."""
    server = DummyServer("workshoptest")
    mod.configure(server, ask=False, port=28015, dir=str(tmp_path))
    return server


def workshop_config(tmp_path):
    """Return the instance's native Workshop config path."""
    return tmp_path / "Servers" / "workshoptest" / "WorkshopDownloadConfig.json"


def test_native_workshop_preserves_operator_ids_and_other_settings(tmp_path):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"File_IDs": [111, "222"], "Ignore_Children_File_IDs": [333],
                                "Download_Timeout": 120, "Operator_Setting": {"keep": True}}))

    mod.configure_workshop(server, ["111", "444"])
    config = json.loads(path.read_text())
    assert config == {"File_IDs": [111, "222", 444], "Ignore_Children_File_IDs": [333],
                      "Download_Timeout": 120, "Operator_Setting": {"keep": True}}
    mod.configure_workshop(server, [])
    assert json.loads(path.read_text())["File_IDs"] == [111, "222"]


def test_native_workshop_reapply_removes_only_previously_managed_ids(tmp_path):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    mod.configure_workshop(server, ["444", "555"])
    config = json.loads(path.read_text())
    config["File_IDs"].append(777)
    path.write_text(json.dumps(config))

    mod.configure_workshop(server, ["555", "666"])
    assert json.loads(path.read_text())["File_IDs"] == [777, 555, 666]
    mod.configure_workshop(server, [])
    assert json.loads(path.read_text())["File_IDs"] == [777]
    assert path.is_file(), "Partial ownership must not delete an operator-editable config"


def test_native_workshop_empty_state_does_not_create_config(tmp_path):
    server = make_server(tmp_path)
    mod.configure_workshop(server, [])
    assert not workshop_config(tmp_path).exists()


def test_failed_native_write_keeps_previous_ownership(tmp_path):
    server = make_server(tmp_path)
    mod.configure_workshop(server, ["444"])
    previous = dict(server.data["mods"]["unturned_workshop_ids"])
    with patch.object(mod, "write_managed_text", side_effect=OSError("disk full")):
        with pytest.raises(OSError, match="disk full"):
            mod.configure_workshop(server, ["555"])
    assert server.data["mods"]["unturned_workshop_ids"] == previous
    assert json.loads(workshop_config(tmp_path).read_text())["File_IDs"] == [444]


def test_native_workshop_preserves_operator_numeric_strings_with_leading_zeroes(tmp_path):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"File_IDs": ["000444"]}')
    mod.configure_workshop(server, ["444"])
    assert json.loads(path.read_text())["File_IDs"] == ["000444"]
    mod.configure_workshop(server, [])
    assert json.loads(path.read_text())["File_IDs"] == ["000444"]


@pytest.mark.parametrize("contents", ["{broken", "[]", '{"File_IDs": "444"}',
                                      '{"File_IDs": [true]}', '{"File_IDs": ["bad"]}'])
def test_native_workshop_rejects_invalid_config_without_overwriting(tmp_path, contents):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(contents)
    with pytest.raises(ServerError):
        mod.configure_workshop(server, ["444"])
    assert path.read_text() == contents


@pytest.mark.parametrize("serverid", ["../outside", "/outside", "nested/instance", ".."])
def test_native_workshop_rejects_unsafe_instance_names(tmp_path, serverid):
    server = make_server(tmp_path)
    server.data["serverid"] = serverid
    with pytest.raises(ServerError):
        mod.configure_workshop(server, ["444"])


def test_native_workshop_rejects_symlinked_instance(tmp_path):
    server = make_server(tmp_path / "install")
    outside = tmp_path / "outside"
    outside.mkdir()
    instances = tmp_path / "install" / "Servers"
    instances.mkdir(parents=True)
    (instances / "workshoptest").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError):
        mod.configure_workshop(server, ["444"])
    assert not list(outside.iterdir())


def test_workshop_is_applied_during_install_and_prestart(tmp_path):
    server = make_server(tmp_path)
    server.data["mods"]["desired"]["workshop"] = [{"workshop_id": "444"}]
    with patch.object(mod, "_base_install"), patch.object(
        mod, "apply_configured_mods", wraps=mod.apply_configured_mods
    ) as apply, patch("server.modsupport.workshop.resolve_workshop_items", return_value={}):
        mod.install(server)
        mod.prestart(server)
    assert apply.call_count == 2
    assert json.loads(workshop_config(tmp_path).read_text())["File_IDs"] == [444]
    assert mod.workshop_app_id == 304930
    assert mod.steam_app_id == 1110390
    assert "mod" in mod.commands
    assert "mod" in mod.command_functions


def test_disabled_workshop_removes_managed_activation_on_prestart(tmp_path):
    server = make_server(tmp_path)
    mod.configure_workshop(server, ["444"])
    server.data["mods"]["enabled"] = False
    mod.prestart(server)
    assert json.loads(workshop_config(tmp_path).read_text())["File_IDs"] == []


def test_cleanup_does_not_reactivate_content_on_next_start(tmp_path):
    server = make_server(tmp_path)
    server.data["mods"]["desired"]["workshop"] = [{"workshop_id": "444"}]
    with patch("server.modsupport.workshop.resolve_workshop_items", return_value={}):
        mod.apply_configured_mods(server)
        mod.cleanup_configured_mods(server)
        mod.prestart(server)
    assert server.data["mods"]["desired"]["workshop"] == []
    assert json.loads(workshop_config(tmp_path).read_text())["File_IDs"] == []


def test_autoapply_false_leaves_config_for_explicit_apply(tmp_path):
    server = make_server(tmp_path)
    server.data["mods"]["autoapply"] = False
    server.data["mods"]["desired"]["workshop"] = [{"workshop_id": "444"}]
    with patch("server.modsupport.workshop.resolve_workshop_items", return_value={}):
        mod.prestart(server)
        assert not workshop_config(tmp_path).exists()
        mod.apply_configured_mods(server)
    assert json.loads(workshop_config(tmp_path).read_text())["File_IDs"] == [444]


def test_workshop_ownership_survives_instance_change(tmp_path):
    server = make_server(tmp_path)
    old_path = workshop_config(tmp_path)
    mod.configure_workshop(server, ["444"])
    server.data["serverid"] = "second"
    mod.configure_workshop(server, ["555"])
    assert json.loads(old_path.read_text())["File_IDs"] == []
    new_path = tmp_path / "Servers" / "second" / "WorkshopDownloadConfig.json"
    assert json.loads(new_path.read_text())["File_IDs"] == [555]
    mod.configure_workshop(server, [])
    assert json.loads(new_path.read_text())["File_IDs"] == []


def test_native_config_sync_also_rejects_symlinked_commands(tmp_path):
    server = make_server(tmp_path)
    commands = tmp_path / "Servers" / server.name / "Server" / "Commands.dat"
    commands.parent.mkdir(parents=True)
    outside = tmp_path / "operator.dat"
    outside.write_text("Name Operator\n")
    commands.symlink_to(outside)
    with pytest.raises(ServerError):
        mod.prestart(server)
    assert outside.read_text() == "Name Operator\n"


def test_instance_migration_rolls_back_if_later_config_write_fails(tmp_path):
    server = make_server(tmp_path)
    mod.configure_workshop(server, ["444"])
    old_path = workshop_config(tmp_path)
    original = old_path.read_text()
    previous = dict(server.data["mods"]["unturned_workshop_ids"])
    server.data["serverid"] = "otherinstance"
    new_path = tmp_path / "Servers" / "otherinstance" / "WorkshopDownloadConfig.json"
    new_path.parent.mkdir(parents=True)
    new_path.write_text('{"File_IDs": [777], "Operator": true}')
    new_original = new_path.read_text()
    real_write = mod.write_managed_text
    calls = []

    def fail_second_write(server, relative, text):
        calls.append(relative)
        if len(calls) == 2:
            raise OSError("disk full")
        return real_write(server, relative, text)

    with patch.object(mod, "write_managed_text", side_effect=fail_second_write):
        with pytest.raises(OSError, match="disk full"):
            mod.configure_workshop(server, ["555"])
    assert old_path.read_text() == original
    assert new_path.read_text() == new_original
    assert server.data["mods"]["unturned_workshop_ids"] == previous


def test_migration_rolls_back_when_later_path_becomes_symlink(tmp_path):
    server = make_server(tmp_path)
    mod.configure_workshop(server, ["444"])
    old_path = workshop_config(tmp_path)
    old_text = old_path.read_text()
    previous = dict(server.data["mods"]["unturned_workshop_ids"])
    server.data["serverid"] = "otherinstance"
    new_path = tmp_path / "Servers" / "otherinstance" / "WorkshopDownloadConfig.json"
    outside = tmp_path / "operator.json"
    outside.write_text('{"File_IDs": [777]}')
    real_write = mod.write_managed_text

    def replace_later_path(server, relative, text):
        if "otherinstance" in relative:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            new_path.symlink_to(outside)
        return real_write(server, relative, text)

    with patch.object(mod, "write_managed_text", side_effect=replace_later_path):
        with pytest.raises(ServerError, match="symlink"):
            mod.configure_workshop(server, ["555"])
    assert old_path.read_text() == old_text
    assert outside.read_text() == '{"File_IDs": [777]}'
    assert server.data["mods"]["unturned_workshop_ids"] == previous


def test_oversized_workshop_config_is_rejected_without_changes(tmp_path):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    path.parent.mkdir(parents=True)
    original = json.dumps({"File_IDs": [777], "Operator": "x" * (1024 * 1024)})
    path.write_text(original)
    with pytest.raises(ServerError, match="size limit"):
        mod.configure_workshop(server, ["444"])
    assert path.read_text() == original
    assert "unturned_workshop_ids" not in server.data["mods"]


def test_rendered_workshop_config_cannot_exceed_read_limit(tmp_path):
    server = make_server(tmp_path)
    path = workshop_config(tmp_path)
    path.parent.mkdir(parents=True)
    # Compact operator JSON fits, but indentation would grow it past the cap.
    original = json.dumps({"File_IDs": [777], "Operator": [0] * 175000})
    assert len(original.encode()) < 1024 * 1024
    path.write_text(original)
    with pytest.raises(ServerError, match="size limit"):
        mod.configure_workshop(server, ["444"])
    assert path.read_text() == original
