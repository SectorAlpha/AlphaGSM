"""Portable download database bootstrap coverage for native binary platforms."""

import importlib
from pathlib import Path

import pytest


@pytest.mark.parametrize("layout", ["bare-filename", "relative-directory", "native-absolute"])
def test_database_bootstrap_creates_file_in_parent_directory(tmp_path, monkeypatch, layout):
    downloader = importlib.import_module("downloader.downloader")
    monkeypatch.chdir(tmp_path)
    if layout == "bare-filename":
        database = Path("db.txt")
    elif layout == "relative-directory":
        database = Path("cache") / "downloads" / "db.txt"
    else:
        database = tmp_path / "native cache" / "downloads" / "db.txt"
    monkeypatch.setattr(downloader, "DB_PATH", str(database))

    assert downloader.getpathifexists("url", ("example",)) is None
    assert database.is_file()
    assert database.read_text(encoding="utf-8") == ""
    database.write_text("url example /cached/payload 1234.0 1\n", encoding="utf-8")
    assert downloader.getpathifexists("url", ("example",)) == "/cached/payload"
    assert database.read_text(encoding="utf-8") == "url example /cached/payload 1234.0 1\n"


@pytest.mark.parametrize("payload", [
    r"C:\Users\User Name\cache é\payload",
    "/home/User  Name/cache é/payload",
    "/cache/tab\tinside/payload",
])
def test_cache_payload_whitespace_survives_lookup_listing_and_reverse_lookup(tmp_path, monkeypatch, payload):
    downloader = importlib.import_module("downloader.downloader")
    database = tmp_path / "cache db.txt"
    monkeypatch.setattr(downloader, "DB_PATH", str(database))
    monkeypatch.setattr(downloader, "USER", None)
    downloads = []

    def download(module, args):
        downloads.append((module, args))
        return payload

    monkeypatch.setattr(downloader, "download", download)
    args = ("https://example.invalid/a file.jar", "server.jar")
    assert downloader.getpath("url", args) == payload
    assert downloader.getpath("url", args) == payload
    assert len(downloads) == 1
    assert downloader.getpathifexists("url", args) == payload
    assert downloader.getargsforpath(payload) == ("url", list(args))
    records = downloader.getpaths(None, active=True, sort="date")
    assert len(records) == 1
    assert records[0][:3] == ("url", list(args), payload)
    assert f" {payload} " in database.read_text(encoding="utf-8")


def test_existing_whitespace_record_keeps_inactive_filter_and_numeric_date_sort(tmp_path, monkeypatch):
    downloader = importlib.import_module("downloader.downloader")
    database = tmp_path / "db.txt"
    monkeypatch.setattr(downloader, "DB_PATH", str(database))
    database.write_text(
        "url newer /cache/user name/new 10.0 1\n"
        "url inactive /cache/user name/hidden 1.0 0\n"
        "url older /cache/user name/old 2.0 1\n",
        encoding="utf-8",
    )
    assert downloader.getpathifexists("url", ("inactive",)) is None
    assert [record[2] for record in downloader.getpaths(None, active=True, sort="date")] == [
        "/cache/user name/old", "/cache/user name/new",
    ]
