"""Unit tests for the top-level self-update command."""

from __future__ import annotations

import importlib
import urllib.error

import pytest


self_update = importlib.import_module("core.self_update")


def test_run_self_update_dispatches_auto_git(monkeypatch):
    calls = []
    monkeypatch.setattr(self_update, "_detect_install_source", lambda: "git")
    monkeypatch.setattr(self_update, "_run_git_self_update", lambda *, check=False: calls.append(check) or 0)

    result = self_update.run_self_update("alphagsm", ["--check"])

    assert result == 0
    assert calls == [True]


def test_run_self_update_rejects_invalid_options(capsys):
    result = self_update.run_self_update("alphagsm", ["--unknown"])

    assert result == 2
    assert "Error parsing arguments and options" in capsys.readouterr().err


def test_git_self_update_refuses_apply_on_developer_branch(monkeypatch):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.3")
    outputs = {
        ("rev-parse", "--abbrev-ref", "HEAD"): "feature/test",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): "origin/feature/test",
        ("rev-parse", "HEAD"): "1111",
        ("rev-parse", "origin/feature/test"): "2222",
        ("merge-base", "HEAD", "origin/feature/test"): "1111",
    }
    monkeypatch.setattr(self_update, "_git_output", lambda args: outputs[tuple(args)])
    monkeypatch.setattr(self_update, "_git_run", lambda args: None)

    with pytest.raises(self_update.SelfUpdateError, match="disabled on developer branch"):
        self_update._run_git_self_update(check=False)


def test_git_self_update_noops_when_current_matches_upstream(monkeypatch, capsys):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.3")
    outputs = {
        ("rev-parse", "--abbrev-ref", "HEAD"): "release_v1",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): "origin/release_v1",
        ("rev-parse", "HEAD"): "1111",
        ("rev-parse", "origin/release_v1"): "1111",
        ("merge-base", "HEAD", "origin/release_v1"): "1111",
    }
    monkeypatch.setattr(self_update, "_git_output", lambda args: outputs[tuple(args)])
    monkeypatch.setattr(self_update, "_git_run", lambda args: None)

    result = self_update._run_git_self_update(check=False)

    assert result == 0
    assert "No update available" in capsys.readouterr().out


def test_git_self_update_pulls_main_branch(monkeypatch):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.3")
    outputs = {
        ("rev-parse", "--abbrev-ref", "HEAD"): "main",
        ("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"): "origin/main",
        ("rev-parse", "HEAD"): "1111",
        ("rev-parse", "origin/main"): "2222",
        ("merge-base", "HEAD", "origin/main"): "1111",
        ("status", "--porcelain"): "",
        ("rev-parse", "--short", "HEAD"): "2222",
    }
    calls = []
    monkeypatch.setattr(self_update, "_git_output", lambda args: outputs[tuple(args)])
    monkeypatch.setattr(self_update, "_git_run", lambda args: calls.append(tuple(args)))

    result = self_update._run_git_self_update(check=False)

    assert result == 0
    assert ("pull", "--ff-only", "origin", "main") in calls


def test_binary_self_update_noops_when_latest_matches_current(monkeypatch, capsys):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.3")
    monkeypatch.setattr(
        self_update,
        "read_json",
        lambda url: {"tag_name": "v1.2.3", "assets": []},
    )

    result = self_update._run_binary_self_update(check=False)

    assert result == 0
    assert "No update available" in capsys.readouterr().out


def test_binary_self_update_treats_non_release_build_as_older(monkeypatch, capsys):
    monkeypatch.setattr(self_update, "get_version", lambda: "8ca961a")
    monkeypatch.setattr(
        self_update,
        "read_json",
        lambda url: {"tag_name": "v1.2.3", "assets": []},
    )

    result = self_update._run_binary_self_update(check=True)

    assert result == 0
    assert "Update available" in capsys.readouterr().out


def test_binary_self_update_refuses_apply_from_source_checkout(monkeypatch):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.2")
    monkeypatch.setattr(
        self_update,
        "read_json",
        lambda url: {"tag_name": "v1.2.3", "assets": []},
    )
    monkeypatch.setattr(self_update.sys, "frozen", False, raising=False)

    with pytest.raises(self_update.SelfUpdateError, match="bundled AlphaGSM binary"):
        self_update._run_binary_self_update(check=False)


def test_binary_self_update_normalizes_release_lookup_failures(monkeypatch):
    monkeypatch.setattr(
        self_update,
        "read_json",
        lambda url: (_ for _ in ()).throw(urllib.error.URLError("down")),
    )

    with pytest.raises(self_update.SelfUpdateError, match="latest AlphaGSM release metadata"):
        self_update._run_binary_self_update(check=False)

@pytest.fixture
def staged_update(monkeypatch, tmp_path):
    """Provide a real installed binary with deterministic release downloads."""
    import hashlib

    current = tmp_path / "install" / "alphagsm"
    current.parent.mkdir()
    current.write_bytes(b"old executable")
    current.chmod(0o751)
    monkeypatch.setattr(self_update.sys, "executable", str(current))
    digest = hashlib.sha256(b"new executable").hexdigest()

    def download(url, target):
        target.write_bytes(b"new executable" if url == "binary" else digest.encode())

    monkeypatch.setattr(self_update, "_download", download)
    return current


def test_replace_binary_stages_on_target_filesystem(monkeypatch, staged_update):
    import errno
    from pathlib import Path

    original_replace = self_update.os.replace

    def same_filesystem_replace(source, target):
        if staged_update.parent not in Path(source).parents:
            raise OSError(errno.EXDEV, "cross-device link")
        return original_replace(source, target)

    monkeypatch.setattr(self_update.os, "replace", same_filesystem_replace)
    self_update._replace_current_binary("binary", "checksum")
    assert staged_update.read_bytes() == b"new executable"
    assert staged_update.stat().st_mode & 0o777 == 0o751
    assert list(staged_update.parent.iterdir()) == [staged_update]


def test_replace_binary_failure_keeps_original_and_cleans_stage(monkeypatch, staged_update):
    def fail_replace(_source, _target):
        raise PermissionError("destination denied")

    monkeypatch.setattr(self_update.os, "replace", fail_replace)
    with pytest.raises(PermissionError):
        self_update._replace_current_binary("binary", "checksum")
    assert staged_update.read_bytes() == b"old executable"
    assert list(staged_update.parent.iterdir()) == [staged_update]


def test_replace_binary_checksum_failure_keeps_original(monkeypatch, staged_update):
    monkeypatch.setattr(self_update, "_download", lambda _url, target: target.write_bytes(b"bad"))
    with pytest.raises(self_update.SelfUpdateError, match="SHA256"):
        self_update._replace_current_binary("binary", "checksum")
    assert staged_update.read_bytes() == b"old executable"
    assert list(staged_update.parent.iterdir()) == [staged_update]


def test_arch_slug_without_uname(monkeypatch):
    import platform

    monkeypatch.delenv("PROCESSOR_ARCHITECTURE", raising=False)
    monkeypatch.delattr(self_update.os, "uname", raising=False)
    monkeypatch.setattr(platform, "machine", lambda: "AMD64")
    assert self_update._arch_slug() == "X64"


def test_windows_update_reports_scheduled_not_completed(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(self_update, "get_version", lambda: "1.2.2")
    monkeypatch.setattr(self_update, "read_json", lambda _url: {"tag_name": "v1.2.3"})
    monkeypatch.setattr(self_update.sys, "frozen", True, raising=False)
    monkeypatch.setattr(self_update.sys, "platform", "win32")
    asset = {"browser_download_url": "https://example.invalid/release"}
    monkeypatch.setattr(self_update, "_select_release_assets", lambda *_args: (asset, asset))
    monkeypatch.setattr(self_update, "_replace_current_binary", lambda *_args: tmp_path / "result.txt")
    assert self_update._run_binary_self_update() == 0
    output = capsys.readouterr().out
    assert "scheduled" in output.lower()
    assert "Updated AlphaGSM binary" not in output


def test_windows_helper_launch_failure_cleans_stage(monkeypatch, staged_update):
    binary_update = importlib.import_module("core.binary_update")
    monkeypatch.setattr(self_update.sys, "platform", "win32")

    def fail_launch(*_args, **_kwargs):
        raise OSError("helper launch denied")

    monkeypatch.setattr(binary_update.subprocess, "Popen", fail_launch)
    with pytest.raises(OSError, match="launch denied"):
        self_update._replace_current_binary("binary", "checksum")
    assert staged_update.read_bytes() == b"old executable"
    assert list(staged_update.parent.iterdir()) == [staged_update]


def test_windows_replace_retains_stage_for_worker(monkeypatch, staged_update):
    binary_update = importlib.import_module("core.binary_update")
    monkeypatch.setattr(self_update.sys, "platform", "win32")
    monkeypatch.setattr(binary_update.subprocess, "Popen", lambda *_args, **_kwargs: None)
    result = self_update._replace_current_binary("binary", "checksum")
    assert staged_update.read_bytes() == b"old executable"
    assert result.is_file()
    assert (result.parent / "replacement.exe").read_bytes() == b"new executable"


@pytest.mark.parametrize("args", [[], ["one", "two"]])
def test_internal_helper_rejects_invalid_arguments(args, capsys):
    assert self_update.run_deferred_update(args) == 2
    assert "Invalid invocation" in capsys.readouterr().err


@pytest.mark.parametrize("machine, expected", [("AMD64", "X64"), ("x86_64", "X64"), ("aarch64", "ARM64"), ("ARM64", "ARM64")])
def test_architecture_aliases(monkeypatch, machine, expected):
    monkeypatch.setattr(self_update.platform, "machine", lambda: machine)
    assert self_update._arch_slug() == expected
