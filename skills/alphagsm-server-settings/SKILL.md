---
name: alphagsm-server-settings
description: "Use when changing AlphaGSM game settings, secrets, map selection or port values."
---

# Change server settings

Inputs: exact tag/config, requested key/value, intended running state. Discover the module's schema instead of assuming generic game keys:

```bash
alphagsm mytf2 set --list
alphagsm mytf2 set gamemap --describe
alphagsm mytf2 set gamemap --values
alphagsm mytf2 set gamemap cp_dustbowl
```

Read the matching guide's settings table and existing values privately when needed. Map-like values must correspond to installed content or supported defaults. `set` validates and persists values; game-config-backed keys sync through the module's declared hook. Manager-only runtime/backup settings are separate. If generated config does not match the accepted value, use [config-sync](../alphagsm-config-sync/SKILL.md) rather than duplicating manual writes that a later start will overwrite.

For port/host-IP/published-port changes inspect the whole claim set. Preserve explicit ownership and reject a collision without moving another server. Use [port-claims](../alphagsm-port-claims/SKILL.md) for implementation defects.

Secret values belong in AlphaGSM's secret path; do not paste them into logs, shell traces, PRs or handoffs. Inspect [secret storage](../../DEVELOPERS.md) before automation supplies secrets; avoid storing literal credentials in reusable examples. `dump` is private diagnostic output, not a routine status report.

Determine whether the actual game needs a restart for this setting. Preserve the requested availability and use a controlled stop/start if necessary. Verify generated config plus [health](../alphagsm-health-check/SKILL.md), or record that the server intentionally remains stopped. On rejection, keep the last known good value and explain the validation error.
