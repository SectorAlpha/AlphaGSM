"""Grouped Terraria game modules.

This package defaults to the vanilla Terraria dedicated server module while
also exposing the existing Terraria variants under a namespaced layout.
"""

from importlib import import_module


def _vanilla_module():
    package_name = __package__ or __name__.rpartition(".")[0]
    return import_module(package_name + ".vanilla")


def __getattr__(name):
    return getattr(_vanilla_module(), name)


def get_start_command(server):
    return _vanilla_module().get_start_command(server)


def get_runtime_requirements(server):
    return _vanilla_module().get_runtime_requirements(server)


def get_container_spec(server):
    return _vanilla_module().get_container_spec(server)