"""TF2 desired-state helpers for curated and workshop mod entries."""

import os
from pathlib import Path

from server import ServerError
from server.modsupport.errors import ModSupportError
from server.modsupport.registry import CuratedRegistryLoader

from .workshop import validate_workshop_id


def ensure_mod_state(server):
    """Seed the TF2 mod datastore shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("curated", [])
    desired.setdefault("workshop", [])
    mods.setdefault("installed", [])
    mods.setdefault("errors", [])
    return mods


def load_tf2_curated_registry():
    """Load the checked-in TF2 curated registry or an override file."""

    override = os.environ.get("ALPHAGSM_TF2_CURATED_REGISTRY_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


def _reject_duplicate_curated_entry(mods, resolved_id):
    for entry in mods["desired"]["curated"]:
        if entry.get("resolved_id") == resolved_id:
            raise ServerError(f"Curated mod '{resolved_id}' is already present in desired state")


def _reject_duplicate_workshop_entry(mods, workshop_id):
    for entry in mods["desired"]["workshop"]:
        if entry.get("workshop_id") == workshop_id:
            raise ServerError(
                f"Workshop item '{workshop_id}' is already present in desired state"
            )


def tf2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the TF2 ``mod`` command desired-state subcommands."""

    del kwargs
    mods = ensure_mod_state(server)
    if action == "list":
        print(mods)
        return
    if action == "add" and source == "curated":
        if not identifier:
            raise ServerError("TF2 mod add curated requires a curated family identifier")
        try:
            resolved = load_tf2_curated_registry().resolve(identifier, extra)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        _reject_duplicate_curated_entry(mods, resolved.resolved_id)
        mods["desired"]["curated"].append(
            {
                "requested_id": identifier,
                "channel": resolved.channel,
                "resolved_id": resolved.resolved_id,
            }
        )
        server.data.save()
        return
    if action == "add" and source == "workshop":
        workshop_id = validate_workshop_id(identifier)
        _reject_duplicate_workshop_entry(mods, workshop_id)
        mods["desired"]["workshop"].append(
            {"workshop_id": workshop_id, "source_type": "workshop"}
        )
        server.data.save()
        return
    raise ServerError("Unsupported TF2 mod command")
