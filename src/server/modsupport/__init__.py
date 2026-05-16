"""Shared curated mod-support registry primitives."""

from .errors import ModSupportError
from .models import CuratedRelease, DesiredModEntry, InstalledModEntry
from .providers import (
    GAMEBANANA_ALLOWED_HOSTS,
    resolve_gamebanana_mod,
    validate_gamebanana_id,
    validate_workshop_id,
)
from .registry import CuratedRegistry, CuratedRegistryLoader

__all__ = [
    "CuratedRegistry",
    "CuratedRegistryLoader",
    "CuratedRelease",
    "GAMEBANANA_ALLOWED_HOSTS",
    "DesiredModEntry",
    "InstalledModEntry",
    "ModSupportError",
    "resolve_gamebanana_mod",
    "validate_gamebanana_id",
    "validate_workshop_id",
]
