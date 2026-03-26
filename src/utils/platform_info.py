"""Platform detection utilities for AlphaGSM.

Provides a single source of truth for the host operating system so that
the rest of the codebase can branch on platform without scattering
``sys.platform`` / ``os.name`` checks everywhere.

Usage::

    from utils.platform_info import PLATFORM, IS_WINDOWS, IS_LINUX, IS_MACOS

The ``PLATFORM`` constant is one of ``'linux'``, ``'windows'``, ``'macos'``,
or ``'unknown'``.
"""

import sys

_SYSTEM = sys.platform  # 'linux', 'win32', 'darwin', 'cygwin', …

if _SYSTEM.startswith("linux"):
    PLATFORM = "linux"
elif _SYSTEM == "win32" or _SYSTEM == "cygwin":
    PLATFORM = "windows"
elif _SYSTEM == "darwin":
    PLATFORM = "macos"
else:
    PLATFORM = "unknown"

IS_WINDOWS = PLATFORM == "windows"
IS_LINUX = PLATFORM == "linux"
IS_MACOS = PLATFORM == "macos"
IS_POSIX = IS_LINUX or IS_MACOS
