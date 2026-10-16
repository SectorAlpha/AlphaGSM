"""Ownership of native Source Workshop subscription lists."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport import native_workshop


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(data={"dir": str(tmp_path), "mods": {}})


def apply(server, ids):
    return native_workshop.apply_managed_workshop_list(server, "insurgency/subscribed_file_ids.txt", ids)


def test_owned_ids_merge_without_claiming_operator_ids_or_comments(server):
    path = Path(server.data["dir"]) / "insurgency/subscribed_file_ids.txt"
    path.parent.mkdir()
    original = "// operator collection\r\n111 // their addon\r\n222\r\n"
    path.write_bytes(original.encode())
    apply(server, ["111", "333"])
    assert path.read_bytes() == (original + "333\n").encode()
    apply(server, [])
    assert path.read_bytes() == original.encode()


def test_created_empty_list_is_removed_without_touching_other_files(server):
    apply(server, ["333"])
    folder = Path(server.data["dir"]) / "insurgency"
    operator = folder / "operator.txt"
    operator.write_text("keep")
    apply(server, [])
    assert not (folder / "subscribed_file_ids.txt").exists()
    assert operator.read_text() == "keep"


def test_external_comments_and_owner_edit_survive_reapply_and_cleanup(server):
    apply(server, ["333"])
    path = Path(server.data["dir"]) / "insurgency/subscribed_file_ids.txt"
    path.write_text("333 // operator took control\n444\n// changed externally\n")
    apply(server, ["333", "555"])
    assert path.read_text() == "333 // operator took control\n444\n// changed externally\n555\n"
    apply(server, [])
    assert path.read_text() == "333 // operator took control\n444\n// changed externally\n"


def test_list_replacement_removes_only_previous_owned_ids(server):
    apply(server, ["333", "444"])
    apply(server, ["444", "555"])
    path = Path(server.data["dir"]) / "insurgency/subscribed_file_ids.txt"
    assert path.read_text() == "444\n555\n"


def test_empty_desired_state_does_not_create_a_list(server):
    assert apply(server, []) == []
    assert not (Path(server.data["dir"]) / "insurgency").exists()


def test_list_rejects_symlinks_and_traversal_without_writes(server, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "insurgency").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match="symlink"):
        apply(server, ["333"])
    with pytest.raises(ServerError, match="contained"):
        native_workshop.apply_managed_workshop_list(server, "../escape.txt", ["333"])
    assert not list(outside.iterdir())


def test_atomic_write_failure_preserves_operator_file_and_ownership(server, monkeypatch):
    apply(server, ["333"])
    path = Path(server.data["dir"]) / "insurgency/subscribed_file_ids.txt"
    before = dict(server.data["mods"]["native_workshop_lists"])
    def fail(*args):
        raise OSError("disk full")
    monkeypatch.setattr(native_workshop, "write_managed_text", fail)
    with pytest.raises(OSError, match="disk full"):
        apply(server, ["444"])
    assert path.read_text() == "333\n"
    assert server.data["mods"]["native_workshop_lists"] == before
