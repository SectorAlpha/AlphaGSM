"""Public package exports for the AlphaGSM server package.

Keep this package import lightweight so helper utilities such as the module
catalog and parity report generator can import ``server.*`` submodules without
eagerly loading the full runtime stack and configuration files.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from .errors import ServerError

__all__ = ["ServerError", "server"]  # Server is lazily exported via __getattr__


def __getattr__(name: str) -> Any:
    """Lazily expose the heavy server module exports on first access."""

    if name == "Server":
        return import_module(".server", __name__).Server
    if name == "server":
        return import_module(".server", __name__)
    if name == "ServerError":
        return ServerError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
