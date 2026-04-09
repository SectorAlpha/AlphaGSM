"""Alias module mapping `cs2server` to the Counter-Strike 2 module."""

from importlib import import_module

ALIAS_TARGET = "counterstrike2"
_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)

def get_runtime_requirements(server):
    return _ALIAS_MODULE.get_runtime_requirements(server)

def get_container_spec(server):
    return _ALIAS_MODULE.get_container_spec(server)
