import errno
import os

from utils.fileutils import make_empty_file


def test_make_empty_file_creates_new_file(tmp_path):
    target = tmp_path / "created.txt"

    make_empty_file(str(target))

    assert target.exists()
    assert target.read_text() == ""


def test_make_empty_file_does_not_change_existing_file(tmp_path):
    target = tmp_path / "existing.txt"
    target.write_text("already here")

    make_empty_file(str(target))

    assert target.read_text() == "already here"


def test_make_empty_file_reraises_unexpected_oserror(monkeypatch, tmp_path):
    target = tmp_path / "error.txt"

    def fake_open(path, flags):
        raise OSError(errno.EACCES, "permission denied")

    monkeypatch.setattr(os, "open", fake_open)

    try:
        make_empty_file(str(target))
    except OSError as ex:
        assert ex.errno == errno.EACCES
    else:
        raise AssertionError("Expected OSError to be reraised")
