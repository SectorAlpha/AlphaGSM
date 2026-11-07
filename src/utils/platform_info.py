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
import platform

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

# Architecture detection
ARCH = platform.machine().lower()

# Normalize common names
if ARCH in ("amd64", "x86_64"):
    ARCH = "x86_64"
elif ARCH in ("i386", "i686", "x86"):
    ARCH = "x86"
elif ARCH in ("arm64", "aarch64"):
    ARCH = "arm64"

IS_64BIT = ARCH in ("x86_64", "arm64") or (hasattr(sys, "maxsize") and sys.maxsize > 2**32)
IS_32BIT = not IS_64BIT
