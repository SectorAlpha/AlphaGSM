---
name: alphagsm-server-migration
description: "Use when moving an AlphaGSM server between hosts with verified data preservation and deliberate cutover."
---

# Migrate a server

Inputs: explicit source/destination access, owner/tag/module, data locations, port/address choices, transfer method, downtime and cutover scope. Read [backup/restore](../alphagsm-backup-restore/SKILL.md), [install-layout](../install-layout/SKILL.md), and destination [preflight](../alphagsm-host-preflight/SKILL.md). There is no AlphaGSM migrate command.

Inventory install tree, worlds/datadir outside it, mods, game config, manager datastore and private secrets. An ordinary game-directory archive does not capture all manager metadata or external data. Record source runtime/version privately and plan new destination paths/ports. Do not copy source claim/runtime identities blindly.

1. Validate destination platform/runtime/storage and establish recoverable transfer scope.
2. Save/stop source when required for consistency; make and retain a verified backup and required owned asset copies.
3. Transfer through the authorized channel; verify archive checksum/contents and private-file permissions. Keep source intact for recovery.
4. Create the same supported module at destination only if its tag is absent. Configure destination settings through set/setup rather than overwriting its whole datastore.
5. Stage required game files/external saves/secrets deliberately. Restore the selected archive if appropriate. Verify paths are visible to the destination Docker daemon.
6. Start via AlphaGSM and verify game readiness, query and info. A staging validation ends with stop/shutdown; a requested cutover deliberately ends with the destination serving.

Example: copy a backed-up Minecraft server to a new host. Recreate tag/module, configure its new install path, restore the selected archive, verify the same world/config, then perform the authorized cutover. Redirect addresses/boot jobs only within that scope. Do not delete source or revoke credentials as an implied cleanup. If destination access/assets are missing, retain a resumable [handoff](../alphagsm-agent-operations/references/evidence-and-handoff.md).
