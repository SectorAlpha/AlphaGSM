"""Alias module mapping `risingstorm2vietnam` to the existing RS2 server module."""

import server.runtime as runtime_module

from importlib import import_module

ALIAS_TARGET = "rs2server"
_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)

def get_runtime_requirements(server):
    return _ALIAS_MODULE.get_runtime_requirements(server)

def get_container_spec(server):
    return _ALIAS_MODULE.get_container_spec(server)
