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