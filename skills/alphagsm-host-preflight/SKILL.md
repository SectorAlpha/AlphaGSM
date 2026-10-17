---
name: alphagsm-host-preflight
description: "Use when checking whether a host and installation can run a selected AlphaGSM server."
---

# Host preflight

Resolve [execution context](../alphagsm-agent-operations/references/execution-context.md). Read the selected game guide and [platform support](../../docs/platform-support.md). Establish available storage, platform/architecture, install directory access, runtime dependencies, and declared AUTH/BYO prerequisites before downloading or starting anything.

Use [server-requirements](../alphagsm-server-requirements/SKILL.md) for each canonical game/version and the [installation policy](../alphagsm-server-requirements/references/approval-gates.md). Separate installer and runtime needs; managed helpers/images can be installed without extra gates. For a vague game request, ask to install if absent or clarify intent if already installed.

Inspect the executable version/help and existing server list. For an existing tag:

```bash
alphagsm mymc doctor --json
alphagsm mymc --help
```

Doctor reports runtime and installation diagnostics; it can fail before setup because files or prerequisites are absent. Inspect individual findings rather than treating that as a successful preflight or reinstall instruction. Before a tag exists, inspect the game's module/runtime declarations and guide; do not create a throwaway production tag merely to run doctor.

For process execution, check the backend plus actual Java, SteamCMD or Wine/Proton requirements. Prefer repository manager/game containers to additional host runtime packages. Check Docker access, effective family/image and mount paths; using existing Docker or acquiring repository images needs no separate permission. Ask before installing genuinely new external host software, including missing Docker/Compose or host Java. Preserve the user's chosen server/fleet scope when changing runtime configuration.

Stop dependent work when credentials, owned assets, destination access or an unsupported platform prevents execution. Continue independent checks and give the exact missing input. Use [system-install-validation](../system-install-validation/SKILL.md) when files exist but cannot run. Complete with a specific readiness checklist; no lifecycle success is implied by this inspection.
