"""Unit tests for the Minecraft jar-download helper modules."""

import importlib


def test_jardownload_module_has_install_function():
    module = importlib.import_module("gamemodules.minecraft.jardownload")
    assert callable(module.install_downloaded_jar)


def test_utils_jardownload_module_has_install_function_and_wrapper_reexports_it():
    wrapper_module = importlib.import_module("gamemodules.minecraft.jardownload")
    utils_module = importlib.import_module("utils.gamemodules.minecraft.jardownload")

    assert callable(utils_module.install_downloaded_jar)
    assert wrapper_module.install_downloaded_jar is utils_module.install_downloaded_jar
