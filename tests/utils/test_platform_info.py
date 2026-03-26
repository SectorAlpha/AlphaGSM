"""Tests for utils.platform_info OS detection module."""

import sys
from unittest.mock import patch

import utils.platform_info as platform_info_module


def _reload_with_platform(fake_platform):
    """Re-import platform_info with sys.platform mocked to *fake_platform*."""
    import importlib

    with patch.object(sys, "platform", fake_platform):
        importlib.reload(platform_info_module)
        result = {
            "PLATFORM": platform_info_module.PLATFORM,
            "IS_WINDOWS": platform_info_module.IS_WINDOWS,
            "IS_LINUX": platform_info_module.IS_LINUX,
            "IS_MACOS": platform_info_module.IS_MACOS,
            "IS_POSIX": platform_info_module.IS_POSIX,
        }
    # Restore real values.
    importlib.reload(platform_info_module)
    return result


def test_linux_detection():
    """sys.platform='linux' produces PLATFORM='linux'."""
    result = _reload_with_platform("linux")
    assert result["PLATFORM"] == "linux"
    assert result["IS_LINUX"] is True
    assert result["IS_WINDOWS"] is False
    assert result["IS_MACOS"] is False
    assert result["IS_POSIX"] is True


def test_linux_variant_detection():
    """sys.platform='linux2' (older CPython) still maps to linux."""
    result = _reload_with_platform("linux2")
    assert result["PLATFORM"] == "linux"
    assert result["IS_LINUX"] is True
    assert result["IS_POSIX"] is True


def test_windows_detection():
    """sys.platform='win32' produces PLATFORM='windows'."""
    result = _reload_with_platform("win32")
    assert result["PLATFORM"] == "windows"
    assert result["IS_WINDOWS"] is True
    assert result["IS_LINUX"] is False
    assert result["IS_MACOS"] is False
    assert result["IS_POSIX"] is False


def test_cygwin_detection():
    """sys.platform='cygwin' maps to windows."""
    result = _reload_with_platform("cygwin")
    assert result["PLATFORM"] == "windows"
    assert result["IS_WINDOWS"] is True
    assert result["IS_POSIX"] is False


def test_macos_detection():
    """sys.platform='darwin' produces PLATFORM='macos'."""
    result = _reload_with_platform("darwin")
    assert result["PLATFORM"] == "macos"
    assert result["IS_MACOS"] is True
    assert result["IS_WINDOWS"] is False
    assert result["IS_LINUX"] is False
    assert result["IS_POSIX"] is True


def test_unknown_detection():
    """An unrecognised sys.platform maps to 'unknown'."""
    result = _reload_with_platform("freebsd13")
    assert result["PLATFORM"] == "unknown"
    assert result["IS_LINUX"] is False
    assert result["IS_WINDOWS"] is False
    assert result["IS_MACOS"] is False
    assert result["IS_POSIX"] is False


def test_current_host_is_consistent():
    """On the current host the flags agree with PLATFORM."""
    p = platform_info_module.PLATFORM
    assert platform_info_module.IS_LINUX == (p == "linux")
    assert platform_info_module.IS_WINDOWS == (p == "windows")
    assert platform_info_module.IS_MACOS == (p == "macos")
    assert platform_info_module.IS_POSIX == (p in ("linux", "macos"))
