"""World deletion must preview, confirm, and stay within the installation."""

from types import SimpleNamespace

import pytest

from server import Server, ServerError
import server.runtime as runtime_module
from utils.cmdparse.cmdparse import parse


@pytest.fixture
def world_server(tmp_path, monkeypatch):
    (tmp_path / "world").mkdir()
    (tmp_path / "world" / "level.dat").write_text("world data")
    (tmp_path / "server.properties").write_text("configuration")
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "example.jar").write_text("plugin")
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    return SimpleNamespace(
        name="example", data={"dir": str(tmp_path)},
        module=SimpleNamespace(wipe_paths=["world"]),
    )


@pytest.mark.parametrize("answer", ["", "n", "no", "anything else"])
def test_wipe_previews_and_cancels_by_default(world_server, monkeypatch, capsys, tmp_path, answer):
    def confirm(prompt):
        assert str(tmp_path / "world") in capsys.readouterr().out
        assert "[y/N]" in prompt
        return answer
    monkeypatch.setattr("builtins.input", confirm)

    Server.wipe(world_server)

    assert (tmp_path / "world" / "level.dat").read_text() == "world data"
    assert "cancel" in capsys.readouterr().out.lower()


@pytest.mark.parametrize("command", ["wipe", "reset-world"])
@pytest.mark.parametrize("yes", [False, True])
def test_wipe_confirmed_removes_only_previewed_world(world_server, monkeypatch, capsys, tmp_path, yes, command):
    def confirm(_prompt):
        assert not yes, "-Y must skip the confirmation prompt"
        return "yes"
    monkeypatch.setattr("builtins.input", confirm)
    args, options = parse(["-Y"] if yes else [], Server.default_command_args[command])

    Server.wipe(world_server, *args, **options)

    output = capsys.readouterr().out
    assert str(tmp_path / "world") in output
    assert "contents" in output
    assert not (tmp_path / "world").exists()
    assert (tmp_path / "server.properties").read_text() == "configuration"
    assert (tmp_path / "plugins" / "example.jar").read_text() == "plugin"


def test_wipe_eof_does_not_delete(world_server, monkeypatch, tmp_path):
    def no_input(_prompt):
        raise EOFError
    monkeypatch.setattr("builtins.input", no_input)
    Server.wipe(world_server)
    assert (tmp_path / "world").exists()


@pytest.mark.parametrize("bad_path", ["", ".", "..", "../outside", "/tmp/outside", "world/.."])
def test_wipe_rejects_unsafe_paths_before_deleting_anything(world_server, bad_path, tmp_path):
    world_server.module.wipe_paths = ["world", bad_path]
    with pytest.raises(ServerError, match="[Uu]nsafe"):
        Server.wipe(world_server, yes=True)
    assert (tmp_path / "world").exists()


@pytest.mark.parametrize("path", ["linked", "linked/world"])
def test_wipe_rejects_symlinked_targets_and_parents(world_server, tmp_path, path):
    (tmp_path / "linked").symlink_to(tmp_path, target_is_directory=True)
    world_server.module.wipe_paths = [path]
    with pytest.raises(ServerError, match="[Ss]ymlink"):
        Server.wipe(world_server, yes=True)
    assert (tmp_path / "world" / "level.dat").exists()


def test_wipe_refuses_server_started_during_confirmation(world_server, monkeypatch, tmp_path):
    def confirm(_prompt):
        monkeypatch.setattr(runtime_module, "check_server_running", lambda server: True)
        return "yes"
    monkeypatch.setattr("builtins.input", confirm)
    with pytest.raises(ServerError, match="running"):
        Server.wipe(world_server)
    assert (tmp_path / "world").exists()


def test_wipe_refuses_changed_targets_after_confirmation(world_server, monkeypatch, tmp_path):
    def confirm(_prompt):
        (tmp_path / "world").rename(tmp_path / "original")
        (tmp_path / "world").mkdir()
        return "yes"
    monkeypatch.setattr("builtins.input", confirm)
    with pytest.raises(ServerError, match="changed"):
        Server.wipe(world_server)
    assert (tmp_path / "world").exists()
    assert (tmp_path / "original" / "level.dat").exists()


def test_wipe_empty_plan_needs_no_confirmation(world_server, monkeypatch, capsys):
    world_server.module.wipe_paths = ["missing"]
    monkeypatch.setattr("builtins.input", lambda prompt: pytest.fail("unexpected prompt"))
    Server.wipe(world_server)
    assert "No world" in capsys.readouterr().out
