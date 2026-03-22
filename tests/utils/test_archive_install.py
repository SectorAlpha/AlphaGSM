"""Tests for utils.archive_install helpers."""

import pytest

from server import ServerError
from utils.archive_install import detect_compression


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("server.zip", "zip"),
        ("server.tar", "tar"),
        ("server.tar.gz", "tar.gz"),
        ("server.tgz", "tar.gz"),
        ("server.tar.bz2", "tar.bz2"),
        ("server.tbz2", "tar.bz2"),
        ("SERVER.ZIP", "zip"),
        ("server.TAR.GZ", "tar.gz"),
    ],
)
def test_detect_compression(filename, expected):
    assert detect_compression(filename) == expected


def test_detect_compression_unknown():
    with pytest.raises(ServerError):
        detect_compression("server.rar")
