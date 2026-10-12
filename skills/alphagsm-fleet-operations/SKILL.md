---
name: alphagsm-fleet-operations
description: "Use when operating an explicitly selected group of AlphaGSM servers and reporting per-server outcomes."
---

# Operate a fleet

Assess [requirements](../alphagsm-server-requirements/SKILL.md) per game/version, then apply the [approval gates](../alphagsm-server-requirements/references/approval-gates.md) to every affected host and dependency batch. Fleet scope does not grant first-use Docker consent or permission for new installs; share an approval only where its explicit scope covers the targets.

Inputs: owner/host/config, enumerated tags, requested operation, maintenance order and failure policy. Resolve [execution context](../alphagsm-agent-operations/references/execution-context.md) and inspect `alphagsm '*' list`. There is no top-level `alphagsm list` command. Expand any authorized wildcard into a concrete inventory before mutation. A named pair never becomes every server or every user.

For inspection, a quoted wildcard is acceptable when all current-user servers were requested:

```bash
alphagsm '*' status
```

For changes, prefer explicit per-tag commands with captured result and verification. Native `alphagsm 2 first second update` processes the group and aggregates failures; it does not provide a transaction or automatic rollback. Do not assume its exit code establishes each server's health.

Example: update `first` and `second`. Inspect each help/state, back up each, run the supported update separately, preserve each requested final state, and check health. If first fails, retain its doctor/log evidence. Continue independent authorized work on second unless shared dependencies or the user-selected failure policy require a stop. Avoid `&&` chains that silently omit the second task.

Sequence shared-resource/migration changes deliberately. Parallel read-only inspection is useful; do not concurrently rewrite the same tag/config or race claim-bearing changes. Bound retries per server to an evidenced correction. Report a table of target, operation, resulting state, health, recovery artifact and blocker. A partial fleet success remains partial.
