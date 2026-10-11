---
name: alphagsm-curated-content
description: "Use when adding curated multiplayer server content or fixing shared payload staging and ownership."
---

# Maintain curated server content

Read [AGENTS.md](../../AGENTS.md), the selected package-local manifest and [modsupport](../../src/server/modsupport). Default scope is hosted multiplayer server content, not client/local/single-player mods. Identify the module's real install capability before researching new families.

Prefer stable authoritative versioned release assets from upstream releases/archives. Resolve unknown payload/compatibility details using upstream docs and actual release metadata. Do not describe a moving latest/channel URL as an immutable pin. Declare dependencies explicitly and test the resolver/apply order.

Distinguish archive-backed Source addons, bare addon-root archives and single `.gma`/`.vpk` files. Inspect staging roots, extraction validation, ownership and cleanup before adding an entry. If the provider's payload differs, fix the shared installer at the root cause first; do not add entries it cannot safely stage/remove.

Keep manifests beside canonical package-backed modules. Intentionally shared cross-module registries remain shared; no fake game package is needed. Preserve manager-owned file boundaries and prevent traversal, symlink escape and deletion of unowned files.

Example: adding a Garry's Mod family that requires ULib must declare that dependency and prove apply installs the prerequisite automatically. Test archive shape/owned paths plus cleanup leaving operator files intact. Existing families without dependencies are not evidence that implicit prerequisite installation works.

Update unit resolution/apply/cleanup coverage, real content lifecycle checks for new payload shapes, matching guide and changelog in the same change. For an operator install request, use [content-operations](../alphagsm-content-operations/SKILL.md). Finish with selected source/version, compatibility evidence, dependency graph and staged/cleaned ownership proof.
