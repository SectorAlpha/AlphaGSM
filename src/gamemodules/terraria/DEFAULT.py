"""Alias module mapping `terraria` to the vanilla Terraria module."""

import server.runtime as runtime_module

from importlib import import_module

ALIAS_TARGET = "terraria.vanilla"
_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)

def get_runtime_requirements(server):
    return _ALIAS_MODULE.get_runtime_requirements(server)

def get_container_spec(server):
    return _ALIAS_MODULE.get_container_spec(server)
