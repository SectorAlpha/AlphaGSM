"""Alias module mapping `arma3.DEFAULT` to the vanilla Arma 3 module."""

import server.runtime as runtime_module

from importlib import import_module

ALIAS_TARGET = "arma3.vanilla"
_ALIAS_MODULE = import_module("gamemodules." + ALIAS_TARGET)

def get_runtime_requirements(server):
    return _ALIAS_MODULE.get_runtime_requirements(server)

def get_container_spec(server):
    return _ALIAS_MODULE.get_container_spec(server)

def get_start_command(server):
    return _ALIAS_MODULE.get_start_command(server)
