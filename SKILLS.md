# AlphaGSM Agent Skills

Use the operations entry skill for server-management requests and the development
entry skill for repository changes. Each selects focused skills as needed; agents
do not need to load the whole library.

Canonical instructions live under `skills/`. Relative links under `.agents/skills/`
provide repository-native discovery. See [packaging conventions](skills/README.md)
and the [agent operations guide](docs/agent-operations.md) for setup and examples.

## Entry points

| Skill | Use when |
| --- | --- |
| [alphagsm-agent-operations](skills/alphagsm-agent-operations/SKILL.md) | asked to run or manage AlphaGSM servers from a broad operational request. |
| [alphagsm-agent-development](skills/alphagsm-agent-development/SKILL.md) | asked to implement, fix or maintain AlphaGSM through a verified repository change. |

## Server operations

| Skill | Use when |
| --- | --- |
| [alphagsm-server-requirements](skills/alphagsm-server-requirements/SKILL.md) | assessing requirements for any game/version/host or encountering a possible dependency install. |
| [alphagsm-backup-restore](skills/alphagsm-backup-restore/SKILL.md) | making or restoring an AlphaGSM backup with an explicit server and recovery target. |
| [alphagsm-boot-activation](skills/alphagsm-boot-activation/SKILL.md) | enabling or disabling AlphaGSM server startup on boot using the existing user scheduler. |
| [alphagsm-console-admin](skills/alphagsm-console-admin/SKILL.md) | reading AlphaGSM server logs, sending game-console input or broadcasting player messages. |
| [alphagsm-content-operations](skills/alphagsm-content-operations/SKILL.md) | applying supported server mods, plugins, addons or maps through AlphaGSM desired state. |
| [alphagsm-fleet-operations](skills/alphagsm-fleet-operations/SKILL.md) | operating an explicitly selected group of AlphaGSM servers and reporting per-server outcomes. |
| [alphagsm-health-check](skills/alphagsm-health-check/SKILL.md) | verifying actual game readiness, query/info health or complete server shutdown. |
| [alphagsm-host-preflight](skills/alphagsm-host-preflight/SKILL.md) | checking whether a host and installation can run a selected AlphaGSM server. |
| [alphagsm-incident-response](skills/alphagsm-incident-response/SKILL.md) | AlphaGSM setup/start crashes, hangs, times out or regresses on a selected server. |
| [alphagsm-runtime-operations](skills/alphagsm-runtime-operations/SKILL.md) | selecting or diagnosing process versus Docker execution for an existing AlphaGSM server. |
| [alphagsm-server-migration](skills/alphagsm-server-migration/SKILL.md) | moving an AlphaGSM server between hosts with verified data preservation and deliberate cutover. |
| [alphagsm-server-provision](skills/alphagsm-server-provision/SKILL.md) | creating, setting up or starting a named AlphaGSM game server unattended. |
| [alphagsm-server-settings](skills/alphagsm-server-settings/SKILL.md) | changing AlphaGSM game settings, secrets, map selection or port values. |
| [alphagsm-server-upgrade](skills/alphagsm-server-upgrade/SKILL.md) | upgrading game server files or the AlphaGSM manager and verifying recovery and health. |
| [alphagsm-world-operations](skills/alphagsm-world-operations/SKILL.md) | creating missing game worlds or resetting explicitly requested configured world data. |

## Repository development

| Skill | Use when |
| --- | --- |
| [alphagsm-module-authoring](skills/alphagsm-module-authoring/SKILL.md) | adding a new dedicated-server game module with lifecycle and runtime coverage. |
| [alphagsm-server-enablement](skills/alphagsm-server-enablement/SKILL.md) | fixing disabled or skipped game servers and closing AlphaGSM support tracker backlog items. |
| [alphagsm-config-sync](skills/alphagsm-config-sync/SKILL.md) | wiring supported set values into real game configuration or fixing lifecycle config drift. |
| [alphagsm-port-claims](skills/alphagsm-port-claims/SKILL.md) | implementing or debugging AlphaGSM port ownership, collision checks and claim-bearing edits. |
| [alphagsm-provider-requirements](skills/alphagsm-provider-requirements/SKILL.md) | implementing provider credentials, tokens, licenses, provisioning or an AUTH/BYO override path. |
| [alphagsm-curated-content](skills/alphagsm-curated-content/SKILL.md) | adding curated multiplayer server content or fixing shared payload staging and ownership. |
| [alphagsm-test-triage](skills/alphagsm-test-triage/SKILL.md) | diagnosing AlphaGSM lint, unit, integration, smoke or CI failures from actual diagnostics. |
| [alphagsm-runtime-validation](skills/alphagsm-runtime-validation/SKILL.md) | verifying AlphaGSM runtime families, branch-local images and process/Docker lifecycle parity. |
| [alphagsm-release-preparation](skills/alphagsm-release-preparation/SKILL.md) | preparing validated AlphaGSM versions, standalone binaries, checksums or release workflow changes. |
| [alphagsm-skill-maintenance](skills/alphagsm-skill-maintenance/SKILL.md) | authoring or validating AlphaGSM skills, discovery links, routing and behavioral evaluations. |

## Existing repository contracts

| Skill | Use when |
| --- | --- |
| [changelog-discipline](skills/changelog-discipline/SKILL.md) | changing release-relevant behavior or workflow expectations and updating AlphaGSM release notes. |
| [disabled-server-gate](skills/disabled-server-gate/SKILL.md) | diagnosing the disabled creation gate or changing a module support state. |
| [docker-runtime-wiring](skills/docker-runtime-wiring/SKILL.md) | implementing or reviewing explicit Docker runtime hooks in an AlphaGSM game module. |
| [install-layout](skills/install-layout/SKILL.md) | changing game install paths, archive extraction, executable lookup or config file layout. |
| [server-info-gathering](skills/server-info-gathering/SKILL.md) | implementing or debugging AlphaGSM query and info protocol hooks. |
| [server-lifecycle](skills/server-lifecycle/SKILL.md) | changing game module lifecycle hooks or checking the AlphaGSM command contract. |
| [smoke-driven-docs](skills/smoke-driven-docs/SKILL.md) | updating server guides or command examples from verified AlphaGSM smoke workflows. |
| [system-install-validation](skills/system-install-validation/SKILL.md) | a downloaded game server cannot start or answer queries on its installed host. |
| [wiki-publishing](skills/wiki-publishing/SKILL.md) | explicitly publishing the wiki or changing the repository documentation mirror. |

## Contracts

Read [AGENTS.md](AGENTS.md) for lifecycle, module layout, port ownership,
config sync, runtime, provider, support-state and release-note requirements.
Skills guide execution within the user’s task and existing authorization.
The [installation/request policy](skills/alphagsm-server-requirements/references/approval-gates.md)
asks to install an absent game, clarifies vague existing-game requests, and gates
only genuinely new software. AlphaGSM-managed steps have no additional approval.
