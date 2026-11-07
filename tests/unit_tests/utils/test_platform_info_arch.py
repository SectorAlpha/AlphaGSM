"""Tests for architecture detection in utils.platform_info."""
import sys
import importlib
from unittest.mock import patch
import utils.platform_info as platform_info_module

def _reload_with_machine(fake_machine, fake_maxsize=None):
    import platform
    importlib.reload(platform_info_module)
    with patch.object(platform, "machine", return_value=fake_machine):
        if fake_maxsize is not None:
            with patch.object(sys, "maxsize", fake_maxsize):
                importlib.reload(platform_info_module)
                result = {
                    "ARCH": platform_info_module.ARCH,
                    "IS_64BIT": platform_info_module.IS_64BIT,
                    "IS_32BIT": platform_info_module.IS_32BIT,
                }
        else:
            importlib.reload(platform_info_module)
            result = {
                "ARCH": platform_info_module.ARCH,
                "IS_64BIT": platform_info_module.IS_64BIT,
                "IS_32BIT": platform_info_module.IS_32BIT,
            }
    importlib.reload(platform_info_module)
    return result

def test_x86_64_detection():
    result = _reload_with_machine("x86_64", 2**63)
    assert result["ARCH"] == "x86_64"
    assert result["IS_64BIT"] is True
    assert result["IS_32BIT"] is False

def test_amd64_detection():
    result = _reload_with_machine("amd64", 2**63)
    assert result["ARCH"] == "x86_64"
    assert result["IS_64BIT"] is True
    assert result["IS_32BIT"] is False

def test_i386_detection():
    result = _reload_with_machine("i386", 2**31)
    assert result["ARCH"] == "x86"
    assert result["IS_64BIT"] is False
    assert result["IS_32BIT"] is True

def test_arm64_detection():
    result = _reload_with_machine("arm64", 2**63)
    assert result["ARCH"] == "arm64"
    assert result["IS_64BIT"] is True
    assert result["IS_32BIT"] is False

def test_aarch64_detection():
    result = _reload_with_machine("aarch64", 2**63)
    assert result["ARCH"] == "arm64"
    assert result["IS_64BIT"] is True
    assert result["IS_32BIT"] is False

def test_x86_detection():
    result = _reload_with_machine("x86", 2**31)
    assert result["ARCH"] == "x86"
    assert result["IS_64BIT"] is False
    assert result["IS_32BIT"] is True

def test_maxsize_override():
    # If ARCH is unknown, fallback to sys.maxsize
    result = _reload_with_machine("unknownarch", 2**63)
    assert result["IS_64BIT"] is True
    result = _reload_with_machine("unknownarch", 2**31)
    assert result["IS_32BIT"] is True
