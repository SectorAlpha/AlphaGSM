"""TF2 desired-state helpers for curated, GameBanana, and workshop mod entries."""

import os
from pathlib import Path

from server import ServerError
from server.modsupport import workshop as workshop_provider
from server.modsupport.native_workshop import build_native_workshop_support
from server.modsupport.owned_payloads import publish_owned_payloads
from server.modsupport.downloads import download_to_cache
from server.modsupport.providers import resolve_gamebanana_mod, resolve_moddb_entry, validate_workshop_id
from server.modsupport.registry import CuratedRegistryLoader
from server.modsupport.source_addons import build_source_addon_mod_support

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
    enabled_sources=("curated", "gamebanana", "moddb"),
    curated_registry_loader=load_tf2_curated_registry,
    curated_identifier_description="curated family identifier",
    download_to_cache_getter=lambda: download_to_cache,
    resolve_gamebanana_mod_getter=lambda: resolve_gamebanana_mod,
    resolve_moddb_entry_getter=lambda: resolve_moddb_entry,
    validate_workshop_id_getter=lambda: validate_workshop_id,
    workshop_app_id=TF2_WORKSHOP_APP_ID,
    prefix_provider_cache_files_with_resolved_id=True,
)

NATIVE_OWNER = 'tf2_native_workshop'
NATIVE_CONFIG = 'tf/cfg/alphagsm_workshop.cfg'


def apply_native_workshop(server, item_ids):
    """Use the engine map loader, retaining engine-owned downloads on cleanup."""
    if item_ids:
        metadata = workshop_provider.resolve_workshop_item_details(item_ids, TF2_WORKSHOP_APP_ID)
        for item, details in metadata.items():
            tags = {tag.get('tag', '').casefold() for tag in details.get('tags', []) if isinstance(tag, dict)}
            map_modes = {'maps', 'map', 'control point', 'capture the flag', 'king of the hill',
                         'payload', 'payload race', 'arena', 'territorial control', 'specialty',
                         'mann vs. machine', 'medieval', 'player destruction', 'robot destruction', 'pass time'}
            if not tags.intersection(map_modes):
                raise ServerError(f'TF2 Workshop item {item} is not a multiplayer map')
    files = {NATIVE_CONFIG: ''.join(f'tf_workshop_map_sync {item}\n' for item in item_ids).encode()} if item_ids else {}
    return publish_owned_payloads(server, NATIVE_OWNER, files)


NATIVE_WORKSHOP = build_native_workshop_support(
    game_label='TF2 maps', workshop_app_id=TF2_WORKSHOP_APP_ID,
    apply_callback=apply_native_workshop,
)


def ensure_mod_state(server):
    """Keep the established addon state together with native map subscriptions."""
    MOD_SUPPORT.ensure_mod_state(server)
    return NATIVE_WORKSHOP.ensure_mod_state(server)


def apply_configured_mods(server):
    """Apply archived addons and native map configuration through one mod action."""
    MOD_SUPPORT.apply_configured_mods(server)
    mods = ensure_mod_state(server)
    if mods['desired']['workshop'] or mods.get('owned_payloads', {}).get(NATIVE_OWNER):
        NATIVE_WORKSHOP.apply_configured_mods(server)


def cleanup_configured_mods(server):
    """Remove only owned native config and established addon-owned files."""
    NATIVE_WORKSHOP.cleanup_configured_mods(server)
    MOD_SUPPORT.cleanup_configured_mods(server)
    ensure_mod_state(server)


def tf2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Keep addon providers and native Workshop ID/URL collections in one command."""
    if source in ('workshop', 'workshop-collection'):
        return NATIVE_WORKSHOP.command_functions['mod'](server, action, source, identifier, extra, **kwargs)
    if action == 'apply':
        return apply_configured_mods(server)
    if action == 'cleanup':
        return cleanup_configured_mods(server)
    return MOD_SUPPORT.command_functions['mod'](server, action, source, identifier, extra, **kwargs)
