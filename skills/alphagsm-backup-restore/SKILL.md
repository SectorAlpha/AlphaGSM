---
name: alphagsm-backup-restore
description: "Use when making or restoring an AlphaGSM backup with an explicit server and recovery target."
---

# Back up and restore

Follow the [installation and request policy](../alphagsm-server-requirements/references/approval-gates.md). AlphaGSM-managed code, helpers, repository image builds and supported prerequisites proceed within the requested task without extra approval. Ask only for new software outside that managed scope, and clarify an unspecified action/target on an existing server.

Inputs: selected tag/config, backup or restore intent, exact archive, acceptable downtime, and final state. Inspect the actual module backup hook as well as help: shared help can advertise an unimplemented hook (TF2 currently has no backup hook). Establish a scoped staged-copy recovery plan or report that capability blocker rather than claiming a backup succeeded. Inspect the module's backup profile and [backup implementation](../../src/utils/backups/backups.py): targets/exclusions and retention determine actual coverage. Minecraft's default profile targets literal `world`, which may differ from its configured world/tag. Verify the actual configured saves are included before claiming recoverability. Mutable data outside the install tree needs deliberate inclusion or a separate staged copy.

```bash
alphagsm mymc backup
alphagsm mymc restore
```

`restore` with no argument lists archives; it is not a restore. Identify the created archive, timestamp/path, size and relevant contents. If the game cannot produce a consistent live backup, stop/save through its supported lifecycle before backup. Preserve the intended running state afterward. Retention may remove old archives; a rollback-critical archive must be retained independently.

For a requested restore, resolve the exact filename instead of reusing an index after another backup may have changed ordering. Confirm the destination and preserve the current state when recovery requires it:

```bash
alphagsm mymc restore "chosen-backup.zip"
```

The current backup helper creates/lists ZIP archives and restore uses unzip. Restore stops a running server automatically and overlays archive contents; files absent from the archive may remain. It does not by itself prove a clean version rollback or complete migration. Do not delete residual files without an established restore plan and scope. Manager datastore/secrets are outside normal game-directory backup coverage.

Verify restored saves/config, then start and [check health](../alphagsm-health-check/SKILL.md) when restoration of service is intended. Validate restore testing in a disposable destination, not against an unrelated live tag. Report actual coverage and recovery artifacts using the [handoff format](../alphagsm-agent-operations/references/evidence-and-handoff.md).
