"""Canonical package import surface for this game module."""

from .main import *  # noqa: F401,F403
from . import main as _main


def __getattr__(name):
    return getattr(_main, name)
