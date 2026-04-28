"""Compatibility wrapper for shared Minecraft jar-download helpers.

Expose `get_start_command` only if the underlying helper provides one; this
keeps static checks happy while remaining a thin compatibility wrapper.
"""

from utils.gamemodules.minecraft.jardownload import *  # noqa: F401,F403
from utils.gamemodules.minecraft.jardownload import get_runtime_requirements, get_container_spec  # noqa: F401

