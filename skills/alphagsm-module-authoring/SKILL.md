---
name: alphagsm-module-authoring
description: "Use when adding a new dedicated-server game module with lifecycle and runtime coverage."
---

# Add a game module

Discover the exact game/version installer and runtime prerequisites with [server-requirements](../alphagsm-server-requirements/SKILL.md). Declare required host tools and provider requirements explicitly; documentation should separate setup-time dependencies from the game runtime. Follow the [approval gates](../alphagsm-server-requirements/references/approval-gates.md) before any new dependency or Docker validation start.

Read [AGENTS.md](../../AGENTS.md), [adding a game](../../docs/adding-a-game-server.md), [server-lifecycle](../server-lifecycle/SKILL.md), and a similar module with passing integration. Establish upstream dedicated-server distribution, platform, license/auth/assets, start/config/stop protocol and multiplayer suitability before coding. Use authoritative upstream research for unknown requirements.

Create `src/gamemodules/<name>/__init__.py` as the stable canonical import and `main.py` for implementation; keep local manifests/assets beside it. Internal family helpers may remain flat. Use the shared factories only when the game fits their behavior. Define command metadata and full lifecycle hooks, correct query/info addresses and graceful runtime-aware input.

Wire [config sync](../alphagsm-config-sync/SKILL.md), [provider requirements](../alphagsm-provider-requirements/SKILL.md), and [port claims](../alphagsm-port-claims/SKILL.md) when applicable. Preserve process launch support and explicit module-scope Docker wrappers; read [docker-runtime-wiring](../docker-runtime-wiring/SKILL.md). Choose the family before building runtime dictionaries.

Add meaningful unit coverage and `tests/integration_tests/test_<module>.py`. The integration must drive AlphaGSM create/setup/start/readiness/status/query/info/info JSON/stop/shutdown, not launch the binary directly. Source servers must answer the real protocol while awake. Container-capable modules also need current-branch Docker lifecycle proof.

Example: a new SteamCMD Linux game should follow a compatible working module's download/config hooks, declare its optional query ports and shared runtime family, then demonstrate both launch paths. Do not copy an app id/start command from a different game without upstream evidence.

Complete with lint 10.00/10, unit/integration/smoke/runtime evidence, guide and changelog, correct public support state and tracker closure. Missing auth/assets are explicit prerequisites; an untested module is not enabled.
