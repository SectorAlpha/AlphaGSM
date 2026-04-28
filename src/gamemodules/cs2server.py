"""Alias module mapping `cs2server` to the Counter-Strike 2 module."""

from importlib import import_module

import server.runtime as runtime_module

ALIAS_TARGET = "counterstrike2"
_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)


def get_runtime_requirements(server):
    """Return the aliased Counter-Strike 2 runtime requirements."""

    return _ALIAS_MODULE.get_runtime_requirements(server)


def get_container_spec(server):
    """Return the aliased Counter-Strike 2 container launch spec."""

    return _ALIAS_MODULE.get_container_spec(server)


def get_start_command(server):
    """Delegate start command to the Counter-Strike 2 module."""

    return _ALIAS_MODULE.get_start_command(server)
