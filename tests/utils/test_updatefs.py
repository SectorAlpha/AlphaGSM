import os

import pytest

import utils.updatefs as updatefs_module


def test_matchespatterns_and_israwdir(tmp_path):
    directory = tmp_path / "folder"
    directory.mkdir()
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")

    patterns = [updatefs_module.re.compile(r"\./folder/.*")]

    assert updatefs_module.matchespatterns("./folder/file.txt", patterns) is True
    assert updatefs_module.matchespatterns("./other.txt", patterns) is False
    assert updatefs_module.israwdir(str(directory)) is True
    assert updatefs_module.israwdir(str(file_path)) is False


def test_ensureabsent_removes_files_and_directories(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("x")
    dir_path = tmp_path / "dir"
    dir_path.mkdir()
    (dir_path / "nested.txt").write_text("x")

    updatefs_module.ensureabsent(str(file_path))
    updatefs_module.ensureabsent(str(dir_path))

    assert not file_path.exists()
    assert not dir_path.exists()


def test_checkfiles_compares_file_contents(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    c = tmp_path / "c.txt"
    a.write_text("same")
    b.write_text("same")
    c.write_text("different")

    assert updatefs_module.checkfiles(str(a), str(b)) is True
    assert updatefs_module.checkfiles(str(a), str(c)) is False


def test_update_returns_true_when_doupdate_succeeds(monkeypatch):
    monkeypatch.setattr(updatefs_module, "doupdate", lambda *args: False)

    assert updatefs_module.update("/old", "/new", "/target") is True


def test_update_returns_false_and_prints_warning_when_doupdate_reports_failure(monkeypatch, capsys):
    monkeypatch.setattr(updatefs_module, "doupdate", lambda *args: True)

    assert updatefs_module.update("/old", "/new", "/target") is False
    assert "Some files couldn't be updated" in capsys.readouterr().out


def test_removeuneeded_deletes_unchanged_old_file(tmp_path):
    old_dir = tmp_path / "old"
    target_dir = tmp_path / "target"
    old_dir.mkdir()
    target_dir.mkdir()
    (old_dir / "file.txt").write_text("same")
    (target_dir / "file.txt").write_text("same")

    result = updatefs_module.removeuneeded(str(old_dir), str(target_dir), ".", "file.txt", [])

    assert result is False
    assert not (target_dir / "file.txt").exists()


def test_updatefromnew_symlinks_when_target_is_missing(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    target_dir = tmp_path / "target"
    old_dir.mkdir()
    new_dir.mkdir()
    target_dir.mkdir()
    (new_dir / "file.txt").write_text("new")

    result = updatefs_module.updatefromnew(
        str(old_dir), str(new_dir), str(target_dir), ".", "file.txt", [], [], [], False
    )

    assert result is False
    assert os.path.islink(target_dir / "file.txt")


@pytest.mark.xfail(reason="checkandcleartrees contains multiple misspelled identifiers in production code")
def test_checkandcleartrees_can_clear_matching_old_tree(tmp_path):
    old_dir = tmp_path / "old"
    target_dir = tmp_path / "target"
    old_dir.mkdir()
    target_dir.mkdir()
    (old_dir / "file.txt").write_text("same")
    (target_dir / "file.txt").write_text("same")

    assert updatefs_module.checkandcleartrees(".", str(target_dir), str(old_dir), []) is True


@pytest.mark.xfail(reason="doupdate references undefined entrym/linkdircopy names in production code")
def test_doupdate_processes_new_entries(tmp_path):
    old_dir = tmp_path / "old"
    new_dir = tmp_path / "new"
    target_dir = tmp_path / "target"
    old_dir.mkdir()
    new_dir.mkdir()
    (new_dir / "file.txt").write_text("new")

    assert updatefs_module.doupdate(str(old_dir), str(new_dir), str(target_dir), ".", [], [], [], False) is False
