import hashlib
import io
from pathlib import Path
import tarfile
import time
from urllib.error import HTTPError, URLError

import pytest

from server.modsupport import downloads as downloads_module
from server.modsupport.downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.ownership import build_owned_manifest


def test_download_to_cache_rejects_untrusted_host(tmp_path):
    with pytest.raises(ModSupportError, match="evil.invalid"):
        download_to_cache(
            "https://evil.invalid/mod.tar.gz",
            allowed_hosts={"trusted.invalid"},
            target_path=tmp_path / "mod.tar.gz",
        )


@pytest.mark.parametrize("error", [
    URLError(ConnectionResetError(104, "Connection reset by peer")),
    TimeoutError("timed out"),
    HTTPError("https://trusted.invalid/mod.zip", 429, "Too Many Requests", {}, None),
    HTTPError("https://trusted.invalid/mod.zip", 503, "Service Unavailable", {}, None),
])
def test_download_to_cache_retries_transient_open_failure(tmp_path, monkeypatch, error):
    calls = []
    sleeps = []

    def fake_urlopen(url, timeout):
        calls.append((url, timeout))
        if len(calls) == 1:
            raise error
        return io.BytesIO(b"complete archive")

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    target = tmp_path / "mod.zip"

    assert download_to_cache(
        "https://trusted.invalid/mod.zip", allowed_hosts={"trusted.invalid"}, target_path=target,
    ) == target
    assert target.read_bytes() == b"complete archive"
    assert len(calls) == 2
    assert sleeps == [1]
    assert list(tmp_path.iterdir()) == [target]


def test_download_to_cache_restarts_stream_and_checksum_after_reset(tmp_path, monkeypatch):
    calls = []

    class InterruptedResponse(io.BytesIO):
        def read(self, size=-1):
            if self.tell():
                raise ConnectionResetError(104, "Connection reset by peer")
            return super().read(size)

    def fake_urlopen(_url, timeout):
        calls.append(timeout)
        return InterruptedResponse(b"partial") if len(calls) == 1 else io.BytesIO(b"complete")

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    target = tmp_path / "mod.zip"
    download_to_cache(
        "https://trusted.invalid/mod.zip", allowed_hosts={"trusted.invalid"}, target_path=target,
        checksum=hashlib.sha256(b"complete").hexdigest(),
    )

    assert target.read_bytes() == b"complete"
    assert calls == [30, 30]
    assert list(tmp_path.iterdir()) == [target]


def test_download_to_cache_exhausts_retries_without_replacing_cache(tmp_path, monkeypatch):
    calls = []
    sleeps = []
    target = tmp_path / "mod.zip"
    target.write_bytes(b"existing cache")

    def fake_urlopen(_url, timeout):
        calls.append(timeout)
        raise URLError(ConnectionResetError(104, "Connection reset by peer"))

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    with pytest.raises(ModSupportError, match="Connection reset by peer"):
        download_to_cache(
            "https://trusted.invalid/mod.zip", allowed_hosts={"trusted.invalid"}, target_path=target,
        )

    assert calls == [30, 30, 30]
    assert sleeps == [1, 2]
    assert target.read_bytes() == b"existing cache"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize("error", [
    HTTPError("https://trusted.invalid/mod.zip", 404, "Not Found", {}, None),
    PermissionError("Permission denied"),
])
def test_download_to_cache_does_not_retry_permanent_errors(tmp_path, monkeypatch, error):
    calls = []
    sleeps = []

    def fake_urlopen(_url, timeout):
        calls.append(timeout)
        raise error

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    with pytest.raises(ModSupportError, match="Failed to download"):
        download_to_cache(
            "https://trusted.invalid/mod.zip", allowed_hosts={"trusted.invalid"},
            target_path=tmp_path / "mod.zip",
        )

    assert calls == [30]
    assert sleeps == []
    assert list(tmp_path.iterdir()) == []


def test_download_to_cache_does_not_retry_or_publish_checksum_mismatch(tmp_path, monkeypatch):
    calls = []
    sleeps = []
    target = tmp_path / "mod.zip"
    target.write_bytes(b"existing cache")

    def fake_urlopen(_url, timeout):
        calls.append(timeout)
        return io.BytesIO(b"unexpected archive")

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)
    monkeypatch.setattr(time, "sleep", sleeps.append)
    with pytest.raises(ModSupportError, match="Checksum mismatch"):
        download_to_cache(
            "https://trusted.invalid/mod.zip", allowed_hosts={"trusted.invalid"}, target_path=target,
            checksum=hashlib.sha256(b"expected archive").hexdigest(),
        )

    assert calls == [30]
    assert sleeps == []
    assert target.read_bytes() == b"existing cache"
    assert list(tmp_path.iterdir()) == [target]


def test_extract_tarball_safe_rejects_path_traversal(tmp_path):
    tar_path = tmp_path / "mod.tar"
    extract_root = tmp_path / "extract"

    with tarfile.open(tar_path, "w") as archive:
        member = tarfile.TarInfo("../escape.txt")
        payload = b"nope"
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))

    with pytest.raises(ModSupportError, match="escape.txt"):
        extract_tarball_safe(tar_path, extract_root)


def test_extract_tarball_safe_rejects_symlink_members(tmp_path):
    tar_path = tmp_path / "mod.tar"
    extract_root = tmp_path / "extract"

    with tarfile.open(tar_path, "w") as archive:
        member = tarfile.TarInfo("tf/addons/link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../outside.txt"
        archive.addfile(member)

    with pytest.raises(ModSupportError, match="link.txt"):
        extract_tarball_safe(tar_path, extract_root)


def test_extract_tarball_safe_rejects_hardlink_members(tmp_path):
    tar_path = tmp_path / "mod.tar"
    extract_root = tmp_path / "extract"

    with tarfile.open(tar_path, "w") as archive:
        file_member = tarfile.TarInfo("tf/addons/real.txt")
        payload = b"ok"
        file_member.size = len(payload)
        archive.addfile(file_member, io.BytesIO(payload))

        link_member = tarfile.TarInfo("tf/addons/hard.txt")
        link_member.type = tarfile.LNKTYPE
        link_member.linkname = "tf/addons/real.txt"
        archive.addfile(link_member)

    with pytest.raises(ModSupportError, match="hard.txt"):
        extract_tarball_safe(tar_path, extract_root)


def test_extract_tarball_safe_does_not_leave_partial_files_when_later_member_is_invalid(tmp_path):
    tar_path = tmp_path / "mod.tar"
    extract_root = tmp_path / "extract"

    with tarfile.open(tar_path, "w") as archive:
        file_member = tarfile.TarInfo("tf/addons/real.txt")
        payload = b"ok"
        file_member.size = len(payload)
        archive.addfile(file_member, io.BytesIO(payload))

        link_member = tarfile.TarInfo("tf/addons/hard.txt")
        link_member.type = tarfile.LNKTYPE
        link_member.linkname = "tf/addons/real.txt"
        archive.addfile(link_member)

    with pytest.raises(ModSupportError, match="hard.txt"):
        extract_tarball_safe(tar_path, extract_root)

    assert not (extract_root / "tf" / "addons" / "real.txt").exists()


def test_install_staged_tree_rejects_paths_outside_allowed_destinations(tmp_path):
    staged_root = tmp_path / "stage"
    server_root = tmp_path / "server"
    (staged_root / "cfg").mkdir(parents=True)
    (staged_root / "cfg" / "server.cfg").write_text("hostname test", encoding="utf-8")

    with pytest.raises(ModSupportError, match="cfg/server.cfg"):
        install_staged_tree(
            staged_root=staged_root,
            server_root=server_root,
            allowed_destinations={"tf/addons", "tf/custom"},
        )


def test_install_staged_tree_rejects_symlinked_file_resolving_outside_staged_root(tmp_path):
    staged_root = tmp_path / "stage"
    server_root = tmp_path / "server"
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("escape", encoding="utf-8")
    (staged_root / "tf" / "addons").mkdir(parents=True)
    (staged_root / "tf" / "addons" / "link.txt").symlink_to(outside_file)

    with pytest.raises(ModSupportError, match="link.txt"):
        install_staged_tree(
            staged_root=staged_root,
            server_root=server_root,
            allowed_destinations={"tf/addons"},
        )


def test_install_staged_tree_does_not_partially_copy_when_later_file_is_rejected(tmp_path):
    staged_root = tmp_path / "stage"
    server_root = tmp_path / "server"
    (staged_root / "tf" / "addons").mkdir(parents=True)
    (staged_root / "cfg").mkdir(parents=True)
    allowed_file = staged_root / "tf" / "addons" / "plugin.vdf"
    allowed_file.write_text("plugin", encoding="utf-8")
    rejected_file = staged_root / "cfg" / "server.cfg"
    rejected_file.write_text("hostname test", encoding="utf-8")

    with pytest.raises(ModSupportError, match="cfg/server.cfg"):
        install_staged_tree(
            staged_root=staged_root,
            server_root=server_root,
            allowed_destinations={"tf/addons"},
        )

    assert not (server_root / "tf" / "addons" / "plugin.vdf").exists()


def test_build_owned_manifest_returns_sorted_relative_paths(tmp_path):
    server_root = tmp_path / "server"
    first = server_root / "tf" / "addons" / "zeta.txt"
    second = server_root / "tf" / "addons" / "alpha.txt"
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_text("z", encoding="utf-8")
    second.write_text("a", encoding="utf-8")

    manifest = build_owned_manifest(server_root, [first, second])

    assert manifest == ["tf/addons/alpha.txt", "tf/addons/zeta.txt"]


def test_download_to_cache_cleans_up_partial_temp_file_on_stream_failure(tmp_path, monkeypatch):
    target_path = tmp_path / "mod.tar.gz"

    class BrokenResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self, _size):
            raise URLError("boom")

    def fake_urlopen(url, timeout):
        assert url == "https://trusted.invalid/mod.tar.gz"
        assert timeout == 30
        return BrokenResponse()

    monkeypatch.setattr(downloads_module, "urlopen", fake_urlopen)

    with pytest.raises(ModSupportError, match="Failed to download"):
        download_to_cache(
            "https://trusted.invalid/mod.tar.gz",
            allowed_hosts={"trusted.invalid"},
            target_path=target_path,
        )

    assert not target_path.exists()
    assert list(tmp_path.iterdir()) == []


def test_download_to_cache_rejects_unsupported_checksum_without_creating_temp_file(tmp_path):
    target_path = tmp_path / "mod.tar.gz"

    with pytest.raises(ModSupportError, match="Unsupported checksum algorithm"):
        download_to_cache(
            "https://trusted.invalid/mod.tar.gz",
            allowed_hosts={"trusted.invalid"},
            target_path=target_path,
            checksum="md5:abc",
        )

    assert not target_path.exists()
    assert list(tmp_path.iterdir()) == []


def test_extract_7z_safe_requires_7z_extractor(tmp_path, monkeypatch):
    monkeypatch.setattr(downloads_module.shutil_module, "which", lambda name: None)

    with pytest.raises(ModSupportError, match="7z-compatible extractor"):
        extract_7z_safe(tmp_path / "mod.7z", tmp_path / "extract")


def test_extract_7z_safe_rejects_unsafe_listed_path(tmp_path, monkeypatch):
    monkeypatch.setattr(downloads_module.shutil_module, "which", lambda name: "/usr/bin/7z")

    class Result:
        def __init__(self, stdout=""):
            self.stdout = stdout
            self.stderr = ""

    def fake_run(args, check, stdout=None, stderr=None, text=None):
        if args[1] == "l":
            return Result(stdout="Path = ../escape.txt\n")
        raise AssertionError("extract should not run when listing is unsafe")

    monkeypatch.setattr(downloads_module.sp, "run", fake_run)

    with pytest.raises(ModSupportError, match="unsafe 7z path"):
        extract_7z_safe(tmp_path / "mod.7z", tmp_path / "extract")


def test_extract_7z_safe_extracts_listed_files(tmp_path, monkeypatch):
    extract_root = tmp_path / "extract"
    monkeypatch.setattr(downloads_module.shutil_module, "which", lambda name: "/usr/bin/7z")

    class Result:
        def __init__(self, stdout=""):
            self.stdout = stdout
            self.stderr = ""

    def fake_run(args, check, stdout=None, stderr=None, text=None):
        if args[1] == "l":
            return Result(stdout="Path = tf/addons/test.vdf\n")
        if args[1] == "x":
            target = extract_root / "tf" / "addons" / "test.vdf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("plugin", encoding="utf-8")
            return Result(stdout="")
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(downloads_module.sp, "run", fake_run)

    extracted = extract_7z_safe(tmp_path / "mod.7z", extract_root)

    assert extracted == [Path(extract_root / "tf" / "addons" / "test.vdf")]
