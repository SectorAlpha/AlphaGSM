from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.reconcile import reconcile_mod_state


def test_reconcile_installs_missing_desired_entries():
    desired = [
        DesiredModEntry(
            source_type="curated",
            requested_id="sourcemod",
            resolved_id="sourcemod.stable",
        )
    ]
    installed = []
    install_calls = []
    remove_calls = []
    installed_entry = InstalledModEntry(
        source_type="curated",
        resolved_id="sourcemod.stable",
        installed_files=["tf/addons/sourcemod.vdf"],
    )

    def install_entry(entry):
        install_calls.append(entry)
        return installed_entry

    def remove_entry(entry):
        remove_calls.append(entry)

    result = reconcile_mod_state(
        desired=desired,
        installed=installed,
        install_entry=install_entry,
        remove_entry=remove_entry,
    )

    assert result == [installed_entry]
    assert install_calls == desired
    assert remove_calls == []


def test_reconcile_keeps_matching_installed_entries_without_reinstall():
    desired_entry = DesiredModEntry(
        source_type="curated",
        requested_id="sourcemod",
        resolved_id="sourcemod.stable",
    )
    installed_entry = InstalledModEntry(
        source_type="curated",
        resolved_id="sourcemod.stable",
        installed_files=["tf/addons/sourcemod.vdf"],
    )
    install_calls = []
    remove_calls = []

    def install_entry(entry):
        install_calls.append(entry)
        raise AssertionError("install_entry should not be called")

    def remove_entry(entry):
        remove_calls.append(entry)

    result = reconcile_mod_state(
        desired=[desired_entry],
        installed=[installed_entry],
        install_entry=install_entry,
        remove_entry=remove_entry,
    )

    assert result == [installed_entry]
    assert install_calls == []
    assert remove_calls == []


def test_reconcile_removes_entries_that_are_no_longer_desired():
    desired_entry = DesiredModEntry(
        source_type="curated",
        requested_id="sourcemod",
        resolved_id="sourcemod.stable",
    )
    kept_entry = InstalledModEntry(
        source_type="curated",
        resolved_id="sourcemod.stable",
        installed_files=["tf/addons/sourcemod.vdf"],
    )
    removed_entry = InstalledModEntry(
        source_type="curated",
        resolved_id="metamod.stable",
        installed_files=["tf/addons/metamod.vdf"],
    )
    install_calls = []
    remove_calls = []

    def install_entry(entry):
        install_calls.append(entry)
        raise AssertionError("install_entry should not be called")

    def remove_entry(entry):
        remove_calls.append(entry)

    result = reconcile_mod_state(
        desired=[desired_entry],
        installed=[removed_entry, kept_entry],
        install_entry=install_entry,
        remove_entry=remove_entry,
    )

    assert result == [kept_entry]
    assert install_calls == []
    assert remove_calls == [removed_entry]
