import importlib
import io
import os
import sys
import urllib.error

import pytest


@pytest.fixture
def url_module(monkeypatch):
    monkeypatch.setenv("ALPHAGSM_CONFIG_LOCATION", "./tests/alphagsm-test.conf")
    sys.modules.pop("downloadermodules.url", None)
    return importlib.import_module("downloadermodules.url")


def test_reporthook_prints_progress_for_known_size(url_module, capsys):
    url_module.reporthook(1, 10, 100)

    captured = capsys.readouterr()
    assert "10.0%" in captured.out


def test_download_rejects_too_many_arguments(url_module, tmp_path):
    with pytest.raises(url_module.DownloaderError, match="Too many arguments"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar", "zip", "extra"))


def test_download_rejects_unknown_decompression(url_module, tmp_path):
    with pytest.raises(url_module.DownloaderError, match="Unknown decompression type"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar", "rar"))


def test_download_wraps_url_errors(url_module, tmp_path, monkeypatch):
    def fake_download_url(url, targetname):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: None)

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))


def test_download_retries_on_url_error_and_succeeds(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []

    def fake_download_url(url, targetname):
        calls.append(url)
        if len(calls) < 2:
            raise urllib.error.URLError("transient")
        with open(targetname, "wb"):
            pass

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == 2
    assert sleeps == [url_module.URL_RETRY_DELAY_SECONDS]


def test_download_raises_after_all_retries_exhausted(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []

    def fake_download_url(url, targetname):
        calls.append(url)
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == url_module.URL_RETRIES
    assert len(sleeps) == url_module.URL_RETRIES - 1


def test_download_removes_partial_file_between_retries(url_module, tmp_path, monkeypatch):
    calls = []
    removed = []
    part_target = str(tmp_path / "server.jar.part")

    def fake_download_url(url, targetname):
        calls.append(url)
        # Simulate a partial file written before failure
        with open(targetname, "wb"):
            pass
        if len(calls) < 2:
            raise urllib.error.URLError("transient")

    real_remove = os.remove

    def fake_remove(path):
        removed.append(path)
        real_remove(path)

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(url_module.os, "remove", fake_remove)

    url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == 2
    assert part_target in removed


@pytest.mark.parametrize(
    ("compression", "expected_cmd"),
    [
        ("zip", ["unzip"]),
        ("tar", ["tar", "-xf"]),
        ("tar.gz", ["tar", "-xf"]),
        ("tgz", ["tar", "-xfz"]),
        ("gz", ["gunzip"]),
    ],
)
def test_download_runs_expected_extractor(url_module, tmp_path, monkeypatch, compression, expected_cmd):
    calls = []

    def fake_download_url(url, targetname):
        with open(targetname, "wb"):
            pass

    def fake_call(cmd, stdout):
        calls.append(cmd)
        return 0

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.sp, "call", fake_call)

    url_module.download(str(tmp_path), ("http://example.com/file", "server", compression))

    assert calls
    assert calls[0][: len(expected_cmd)] == expected_cmd


def test_download_raises_when_extractor_fails(url_module, tmp_path, monkeypatch):
    def fake_download_url(url, targetname):
        with open(targetname, "wb"):
            pass

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.sp, "call", lambda cmd, stdout: 1)

    with pytest.raises(url_module.DownloaderError, match="Error extracting download"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server", "zip"))


def test_getfilter_filters_by_active_and_url(url_module):
    filterfn, sortfn = url_module.getfilter(active=True, url=r"http://example.com/.*", sort="date")

    assert sortfn is not None
    assert filterfn("url", ["http://example.com/file"], "/tmp/path", 1.0, True)
    assert not filterfn("url", ["http://other.example/file"], "/tmp/path", 1.0, True)


def test_getfilter_allows_unsorted_requests(url_module):
    with pytest.raises(url_module.DownloaderError, match="Unknown sort key"):
        url_module.getfilter()
