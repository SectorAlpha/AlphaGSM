import importlib
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
        url_module.download(
            str(tmp_path),
            ("http://example.com/file", "server.jar", "zip", "120", "curl", "extra"),
        )


def test_download_rejects_unknown_decompression(url_module, tmp_path):
    with pytest.raises(url_module.DownloaderError, match="Unknown decompression type"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar", "rar"))


def test_download_wraps_url_errors(url_module, tmp_path, monkeypatch):
    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: None)

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))


def test__download_url_falls_back_to_curl_on_url_error(url_module, tmp_path, monkeypatch):
    calls = []

    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("timed out")

    def fake_curl(url, targetname, timeout, resume=False, retries=url_module.URL_RETRIES):
        calls.append((url, targetname, timeout, resume, retries))
        with open(targetname, "wb"):
            pass
        return targetname

    monkeypatch.setattr(url_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(url_module, "_download_url_with_curl", fake_curl)

    target = tmp_path / "server.zip"
    result = url_module._download_url("http://example.com/file", str(target), timeout=300)

    assert result == str(target)
    assert calls == [("http://example.com/file", str(target), 300, False, url_module.URL_RETRIES)]


def test__download_url_preserves_original_error_when_curl_unavailable(url_module, tmp_path, monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("timed out")

    def fake_curl(url, targetname, timeout, resume=False, retries=url_module.URL_RETRIES):
        raise FileNotFoundError("curl missing")

    monkeypatch.setattr(url_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(url_module, "_download_url_with_curl", fake_curl)

    with pytest.raises(urllib.error.URLError, match="timed out"):
        url_module._download_url("http://example.com/file", str(tmp_path / "server.zip"), timeout=300)


def test__download_url_with_curl_raises_os_error_on_failure(url_module, tmp_path, monkeypatch):
    monkeypatch.setattr(url_module.shutil, "which", lambda name: "/usr/bin/curl")
    monkeypatch.setattr(
        url_module.sp,
        "run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 22, "stderr": "curl: (22) 404"})(),
    )

    with pytest.raises(OSError, match=r"curl: \(22\) 404"):
        url_module._download_url_with_curl("http://example.com/file", str(tmp_path / "server.zip"), 300)


def test__download_url_with_curl_forces_http11(url_module, tmp_path, monkeypatch):
    commands = []

    monkeypatch.setattr(url_module.shutil, "which", lambda name: "/usr/bin/curl")

    def fake_run(command, **kwargs):
        commands.append(command)
        return type("Result", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(url_module.sp, "run", fake_run)

    url_module._download_url_with_curl("http://example.com/file", str(tmp_path / "server.zip"), 300)

    assert commands
    assert "--http1.1" in commands[0]
    retry_index = commands[0].index("--retry")
    assert commands[0][retry_index + 1] == str(url_module.URL_RETRIES)


def test_download_retries_on_url_error_and_succeeds(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        calls.append((url, timeout))
        if len(calls) < 2:
            raise urllib.error.URLError("transient")
        with open(targetname, "wb"):
            pass

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == 2
    assert calls == [("http://example.com/file", url_module.URL_TIMEOUT_SECONDS)] * 2
    assert sleeps == [url_module.URL_RETRY_DELAY_SECONDS]


def test_download_retries_on_os_error_and_succeeds(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        calls.append((url, timeout))
        if len(calls) < 2:
            raise OSError("Remote end closed connection without response")
        with open(targetname, "wb"):
            pass

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == 2
    assert calls == [("http://example.com/file", url_module.URL_TIMEOUT_SECONDS)] * 2
    assert sleeps == [url_module.URL_RETRY_DELAY_SECONDS]


def test_download_raises_after_all_retries_exhausted(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        calls.append((url, timeout))
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))

    assert len(calls) == url_module.URL_RETRIES
    assert calls == [("http://example.com/file", url_module.URL_TIMEOUT_SECONDS)] * url_module.URL_RETRIES
    assert len(sleeps) == url_module.URL_RETRIES - 1


def test_download_wraps_os_errors(url_module, tmp_path, monkeypatch):
    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        raise OSError("Remote end closed connection without response")

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: None)

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.jar"))


def test_download_removes_partial_file_between_retries(url_module, tmp_path, monkeypatch):
    calls = []
    removed = []
    part_target = str(tmp_path / "server.jar.part")

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        calls.append((url, timeout))
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
    assert calls == [("http://example.com/file", url_module.URL_TIMEOUT_SECONDS)] * 2
    assert part_target in removed


def test_download_accepts_custom_timeout(url_module, tmp_path, monkeypatch):
    calls = []

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
        calls.append((url, timeout))
        with open(targetname, "wb"):
            pass

    monkeypatch.setattr(url_module, "_download_url", fake_download_url)
    monkeypatch.setattr(url_module.sp, "call", lambda cmd, stdout: 0)

    url_module.download(str(tmp_path), ("http://example.com/file", "server.zip", "zip", "300"))

    assert calls == [("http://example.com/file", 300)]


def test_download_rejects_invalid_timeout(url_module, tmp_path):
    with pytest.raises(url_module.DownloaderError, match="Invalid download timeout"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.zip", "zip", "0"))


def test_download_rejects_invalid_transport(url_module, tmp_path):
    with pytest.raises(url_module.DownloaderError, match="Invalid download transport"):
        url_module.download(str(tmp_path), ("http://example.com/file", "server.zip", "zip", "300", "wget"))


def test_download_uses_curl_transport_with_resume(url_module, tmp_path, monkeypatch):
    calls = []
    sleeps = []
    part_target = tmp_path / "server.zip.part"

    def fake_download_url_with_curl(url, targetname, timeout, resume=False, retries=url_module.URL_RETRIES):
        calls.append((url, targetname, timeout, resume, retries))
        with open(targetname, "ab") as handle:
            handle.write(b"data")
        if len(calls) < 2:
            raise OSError("Remote end closed connection without response")

    monkeypatch.setattr(url_module, "_download_url_with_curl", fake_download_url_with_curl)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(url_module.sp, "call", lambda cmd, stdout: 0)

    url_module.download(
        str(tmp_path),
        ("http://example.com/file", "server.zip", "zip", "300", "curl"),
    )

    assert calls == [
        ("http://example.com/file", str(part_target), 300, False, 0),
        ("http://example.com/file", str(part_target), 300, True, 0),
    ]
    assert sleeps == [url_module.URL_RETRY_DELAY_SECONDS]


def test_download_with_curl_transport_keeps_partial_between_retries(url_module, tmp_path, monkeypatch):
    removed = []
    part_target = tmp_path / "server.zip.part"

    def fake_download_url_with_curl(url, targetname, timeout, resume=False, retries=url_module.URL_RETRIES):
        with open(targetname, "ab") as handle:
            handle.write(b"data")
        raise OSError("Remote end closed connection without response")

    real_remove = os.remove

    def fake_remove(path):
        removed.append(path)
        real_remove(path)

    monkeypatch.setattr(url_module, "_download_url_with_curl", fake_download_url_with_curl)
    monkeypatch.setattr(url_module.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(url_module.os, "remove", fake_remove)

    with pytest.raises(url_module.DownloaderError, match="Can't download file"):
        url_module.download(
            str(tmp_path),
            ("http://example.com/file", "server.zip", "zip", "300", "curl"),
        )

    assert removed == [str(part_target)]


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

    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
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
    def fake_download_url(url, targetname, timeout=url_module.URL_TIMEOUT_SECONDS):
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
