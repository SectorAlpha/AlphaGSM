"""Unit tests for the minecraft.jardownload helper module."""

import importlib


def test_jardownload_module_has_install_function():
    module = importlib.import_module("gamemodules.minecraft.jardownload")
    assert callable(module.install_downloaded_jar)
