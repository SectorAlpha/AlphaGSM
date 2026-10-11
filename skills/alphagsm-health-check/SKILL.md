---
name: alphagsm-health-check
description: "Use when verifying actual game readiness, query/info health or complete server shutdown."
---

# Verify server health

Inputs: exact tag/config, expected running state, game protocol and deadline. Start with:

```bash
alphagsm mytf2 status
alphagsm mytf2 query
alphagsm mytf2 info --json
alphagsm mytf2 logs -n 150
```

Read the module's query/info hooks and matching smoke/integration readiness helpers. Inspect both exit code and returned payload: a live process or an empty/fallback result does not establish readiness. Poll the real protocol with a finite game-appropriate deadline, allowing normal startup time; retain the last error and log tail on timeout.

For Source servers, require real A2S query/info. Hibernation logs and TCP fallback are insufficient; use the game's documented keep-awake/wake mechanism and the TF2 smoke settings when applicable. For Minecraft use SLP and the declared address. Docker health checks may need the module's internal namespace probe; a host socket check can test the wrong endpoint.

A running-service task completes after readiness, status, query, info and info JSON establish the expected state. A stop task completes after the owned process/container ends and its claimed listeners close; do not infer shutdown solely from the stop command returning. Report any protocol fallback explicitly.

Example: TF2 reports running but A2S fails. Record it as unhealthy, retain diagnostics, then route to [incident-response](../alphagsm-incident-response/SKILL.md) and [server-info-gathering](../server-info-gathering/SKILL.md). Do not promote a support tracker from this incomplete result.
