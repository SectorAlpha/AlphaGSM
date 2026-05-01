"""TF2 desired-state helpers for curated, GameBanana, and workshop mod entries."""

import os
from pathlib import Path

from server.modsupport.downloads import download_to_cache
from server.modsupport.providers import resolve_gamebanana_mod, resolve_moddb_entry, validate_workshop_id
from server.modsupport.registry import CuratedRegistryLoader
from server.modsupport.source_addons import build_source_addon_mod_support
import utils.steamcmd as steamcmd

from .layout import ALLOWED_TF2_MOD_DESTINATIONS


TF2_WORKSHOP_APP_ID = 440


def load_tf2_curated_registry():
    """Load the checked-in TF2 curated registry or an override file."""

    override = os.environ.get("ALPHAGSM_TF2_CURATED_REGISTRY_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="TF2",
    game_dir="tf",
    cache_namespace="",
    direct_url_suffixes={},
    direct_url_filename_description="a supported archive filename",
    allowed_destinations=ALLOWED_TF2_MOD_DESTINATIONS,
    enabled_sources=("curated", "gamebanana", "moddb", "workshop"),
    curated_registry_loader=load_tf2_curated_registry,
    curated_identifier_description="curated family identifier",
    download_to_cache_getter=lambda: download_to_cache,
    resolve_gamebanana_mod_getter=lambda: resolve_gamebanana_mod,
    resolve_moddb_entry_getter=lambda: resolve_moddb_entry,
    validate_workshop_id_getter=lambda: validate_workshop_id,
    workshop_downloader_getter=lambda: steamcmd.download_workshop_item,
    workshop_app_id=TF2_WORKSHOP_APP_ID,
    prefix_provider_cache_files_with_resolved_id=True,
)

ensure_mod_state = MOD_SUPPORT.ensure_mod_state
apply_configured_mods = MOD_SUPPORT.apply_configured_mods
cleanup_configured_mods = MOD_SUPPORT.cleanup_configured_mods
tf2_mod_command = MOD_SUPPORT.command_functions["mod"]
