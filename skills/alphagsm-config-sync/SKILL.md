---
name: alphagsm-config-sync
description: "Use when wiring supported set values into real game configuration or fixing lifecycle config drift."
---

# Wire game config sync

Inspect the module configure/checkvalue/install/prestart/update paths and [config sync contract](../../AGENTS.md). Find the game file/live payload each supported key actually represents. Schema discovery in [settable keys](../../src/server/settable_keys.py) helps distinguish game settings from manager metadata.

Add one `sync_server_config(server)` helper and declare `config_sync_keys` for top-level real game values. Reuse the helper through relevant lifecycle paths instead of duplicating writes. Preserve unrelated user config where the format allows it. Exclude backup/runtime/image/cache/install-only keys; setting these must not rewrite game config.

Validate map/world/level/mission values against installed content, known defaults or a game-specific allowlist when practical. Report invalid input through the module's existing ServerError path. Do not accept arbitrary path traversal or replace an unrelated save simply to make a map key work.

Example: changing port should update the real game config through the shared sync helper, while changing a backup profile should leave that file untouched. Add a test that proves both effects and invalid-value behavior, including setup/prestart/update reuse where it changes behavior.

Use `scripts/list_missing_config_sync_contracts.py` for audit findings, reading its CLI before running. Keep [runtime wrappers](../docker-runtime-wiring/SKILL.md) aligned with changed launch/config fields and test claim-bearing edits through [port-claims](../alphagsm-port-claims/SKILL.md). Complete with accepted set value, generated config, restart/readiness evidence when relevant, regression tests and matching guide/changelog.
