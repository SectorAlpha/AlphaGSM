---
name: alphagsm-content-operations
description: "Use when applying supported server mods, plugins, addons or maps through AlphaGSM desired state."
---

# Operate server content

Read [installing mods](../../docs/installing-mods.md), matching game guide and `<tag> --help`. Inputs include the exact server-compatible family/source/version, initialized install and allowed downtime. Not every module exposes mod/map commands; Palworld has no manager mod installer today. Unsupported Workshop desired state is not an apply capability.

For TF2, request both prerequisites explicitly where the checked-in registry does not declare dependency wiring:

```bash
alphagsm mytf2 mod add manifest metamod
alphagsm mytf2 mod add manifest sourcemod
alphagsm mytf2 mod apply
alphagsm mytf2 mod list
```

`add` records intent; only `apply` downloads/stages owned files. Inspect the selected registry release and declared dependencies instead of assuming a version/channel is immutable or dependencies are always automatic. Prefer upstream versioned artifacts when a specific pin is requested; explain a channel URL's moving nature rather than calling it a reproducible version.

Back up affected config/content before replacement; stop/restart when the game's loader requires it. Verify staging and game/plugin load logs plus [health](../alphagsm-health-check/SKILL.md). A file on disk alone does not prove successful loading. For TF2 maps use `map add curated <family>`, apply and list, then select only a validated installed map via the correct setting.

`mod cleanup` removes AlphaGSM-owned files and can affect the entire tracked addon set; do not treat it as a one-plugin remove command. Inspect its scope before using it. Never delete unowned addons manually to mask an ownership error. Payload/ownership defects belong in [curated-content](../alphagsm-curated-content/SKILL.md). Report desired, staged and loaded state separately.
