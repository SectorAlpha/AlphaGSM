---
name: alphagsm-world-operations
description: "Use when creating missing game worlds or resetting explicitly requested configured world data."
---

# Manage worlds

Before creating a world through start or restarting after reset, apply the [Docker and installation approval gates](../alphagsm-server-requirements/references/approval-gates.md). A world request does not authorize first-use Docker startup or missing runtime/image installations; inspect and obtain the required approvals first.

Read [world management](../../docs/world-management.md) and the selected module's help/settings. Resolve the configured world and exact existing save paths. `reset-world`/`wipe` take no world-name argument and have no dry-run flag. A request to reset a different named world cannot be fulfilled by blindly deleting the currently configured one.

For first-world creation on Terraria/TShock/Necesse:

```bash
alphagsm myserver start --autocreate
```

This creates only a missing configured world and leaves an existing one unchanged. Minecraft/Rust generate missing worlds through ordinary start. Necesse `datadir` points at existing saves; changing it does not migrate them.

For an explicitly authorized reset, preserve a backup if recovery is wanted, stop and verify shutdown, inspect configured-world metadata and the documented module target rules. The normal prompt prints actual targets before confirmation:

```bash
alphagsm myserver stop
alphagsm myserver reset-world
```

For unattended execution, use `-Y` only after the exact target scope has been independently established and deletion is authorized. Do not send speculative confirmation to an interactive command. Paper includes its configured dimensions; Rust's supported reset excludes blueprints and custom identities/maps. Unexpected paths or unsupported modules are blockers, not grounds for a broad filesystem delete.

Verify only intended saves were removed and config/plugins/unrelated worlds survived. Create a replacement and [verify health](../alphagsm-health-check/SKILL.md) only when requested. Record scope and retained backup; broad server management permission does not imply permission to reset progress.
