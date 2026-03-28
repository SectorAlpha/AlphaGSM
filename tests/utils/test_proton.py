"""Unit tests for utils.proton – Wine/Proton wrapping helpers."""

import os
import types

import pytest

import utils.proton as proton_module


# ---------------------------------------------------------------------------
# find_wine
# ---------------------------------------------------------------------------

def test_find_wine_returns_none_when_not_found(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    assert proton_module.find_wine() is None


def test_find_wine_returns_path_when_present(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    assert proton_module.find_wine() == "/usr/bin/wine"


# ---------------------------------------------------------------------------
# find_proton
# ---------------------------------------------------------------------------

def test_find_proton_returns_none_when_no_search_dirs_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "nonexistent")])
    assert proton_module.find_proton() is None


def test_find_proton_returns_proton_script_when_found(tmp_path, monkeypatch):
    # Simulate GE-Proton9-27/proton inside a search dir
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    assert proton_module.find_proton() == str(proton_exe)


def test_find_proton_returns_latest_version(tmp_path, monkeypatch):
    """When multiple tool dirs exist, the lexicographically last is preferred."""
    compat = tmp_path / "compat"
    for name in ("GE-Proton8-10", "GE-Proton9-27"):
        d = compat / name
        d.mkdir(parents=True)
        (d / "proton").write_text("#!/bin/bash\n")

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(compat)])
    result = proton_module.find_proton()
    assert "GE-Proton9-27" in result


def test_find_proton_skips_non_directory_entries(tmp_path, monkeypatch):
    """Loose files in the search dir are ignored; only subdirs with proton count."""
    compat = tmp_path / "compat"
    compat.mkdir()
    (compat / "not-a-dir.tar.gz").write_text("")  # a file, not a dir

    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(compat)])
    assert proton_module.find_proton() is None


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

def test_is_available_false_when_neither(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [])
    assert proton_module.is_available() is False


def test_is_available_true_when_wine_present(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    assert proton_module.is_available() is True


def test_is_available_true_when_proton_found(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-01"
    tool_dir.mkdir(parents=True)
    (tool_dir / "proton").write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    assert proton_module.is_available() is True


# ---------------------------------------------------------------------------
# wrap_command – Wine paths
# ---------------------------------------------------------------------------

def test_wrap_command_with_wine_no_prefix(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe"])
    assert result == ["env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "/usr/bin/wine", "server.exe"]


def test_wrap_command_with_wine_and_prefix(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe"], wineprefix="/srv/game/.wine")
    assert result == ["env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "WINEPREFIX=/srv/game/.wine", "/usr/bin/wine", "server.exe"]


def test_wrap_command_preserves_trailing_args(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: "/usr/bin/wine" if name == "wine" else None)
    result = proton_module.wrap_command(["server.exe", "--port", "7000"])
    assert result == ["env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "/usr/bin/wine", "server.exe", "--port", "7000"]


# ---------------------------------------------------------------------------
# wrap_command – Proton paths (wine absent)
# ---------------------------------------------------------------------------

def test_wrap_command_uses_proton_when_wine_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])
    monkeypatch.setattr(proton_module.os.path, "expanduser", lambda p: str(tmp_path / ".proton"))

    result = proton_module.wrap_command(["server.exe"])
    assert result[0] == "env"
    assert any("STEAM_COMPAT_DATA_PATH=" in tok for tok in result)
    assert str(proton_exe) in result
    assert "run" in result
    assert "server.exe" in result


def test_wrap_command_uses_wineprefix_for_proton_compat_path(tmp_path, monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    tool_dir = tmp_path / "compat" / "GE-Proton9-27"
    tool_dir.mkdir(parents=True)
    proton_exe = tool_dir / "proton"
    proton_exe.write_text("#!/bin/bash\n")
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [str(tmp_path / "compat")])

    custom_prefix = str(tmp_path / "myprefix")
    result = proton_module.wrap_command(["server.exe"], wineprefix=custom_prefix)
    assert f"STEAM_COMPAT_DATA_PATH={custom_prefix}" in result


# ---------------------------------------------------------------------------
# wrap_command – error when nothing available
# ---------------------------------------------------------------------------

def test_wrap_command_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(proton_module.shutil, "which", lambda name: None)
    monkeypatch.setattr(proton_module, "_PROTON_SEARCH_DIRS", [])
    with pytest.raises(RuntimeError, match="[Ww]ine"):
        proton_module.wrap_command(["server.exe"])
