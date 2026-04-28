"""Helpers for reconciling desired and installed mod state."""

from __future__ import annotations

from server.modsupport.models import DesiredModEntry, InstalledModEntry


def reconcile_mod_state(*, desired, installed, install_entry, remove_entry) -> list[InstalledModEntry]:
    """Reconcile desired mod entries against the current installed state."""
    installed_by_resolved_id = {
        entry.resolved_id: entry for entry in installed
    }
    desired_resolved_ids = {
        entry.resolved_id for entry in desired if entry.resolved_id is not None
    }
    new_installed_state: list[InstalledModEntry] = []

    for desired_entry in desired:
        installed_entry = installed_by_resolved_id.get(desired_entry.resolved_id)
        if installed_entry is not None:
            new_installed_state.append(installed_entry)
            continue
        new_installed_state.append(install_entry(desired_entry))

    for installed_entry in installed:
        if installed_entry.resolved_id not in desired_resolved_ids:
            remove_entry(installed_entry)

    return new_installed_state
