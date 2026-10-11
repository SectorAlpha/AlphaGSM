---
name: alphagsm-host-preflight
description: "Use when checking whether a host and installation can run a selected AlphaGSM server."
---

# Host preflight

Resolve [execution context](../alphagsm-agent-operations/references/execution-context.md). Read the selected game guide and [platform support](../../docs/platform-support.md). Establish available storage, platform/architecture, install directory access, runtime dependencies, and declared AUTH/BYO prerequisites before downloading or starting anything.

Inspect the executable version/help and existing server list. For an existing tag:

```bash
alphagsm mymc doctor --json
alphagsm mymc --help
```

Doctor reports runtime and installation diagnostics; it can fail before setup because files or prerequisites are absent. Inspect individual findings rather than treating that as a successful preflight or reinstall instruction. Before a tag exists, inspect the game's module/runtime declarations and guide; do not create a throwaway production tag merely to run doctor.

For process execution, check the selected backend plus Java, SteamCMD libraries or Wine/Proton as required. For Docker, check daemon access, effective family/image and host-visible mount paths. Inspect, then install missing prerequisites only within the authorized host setup. Do not change the global backend for a single-server task without checking the other servers it affects.

Stop dependent work when credentials, owned assets, destination access or an unsupported platform prevents execution. Continue independent checks and give the exact missing input. Use [system-install-validation](../system-install-validation/SKILL.md) when files exist but cannot run. Complete with a specific readiness checklist; no lifecycle success is implied by this inspection.
