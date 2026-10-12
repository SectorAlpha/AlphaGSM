---
name: alphagsm-server-requirements
description: "Use when assessing prerequisites for any AlphaGSM game type, selected version or host, or when setup, start, repair or testing could install dependencies."
---

# Assess game-server requirements

Before provisioning or repairing a server, establish what the selected game
actually needs. Resolve [execution context](../alphagsm-agent-operations/references/execution-context.md)
and read the [installation and request policy](references/approval-gates.md).
Apply this to every selected canonical module, including aliases and family
variants; a family name alone is not a complete requirement list.

## Resolve intent first

Inspect the selected user's inventory and actual install files, matching canonical
ids and aliases. Apply the [request decision table](references/approval-gates.md):
for a vague request with no installed game, ask to install; with an existing game,
clarify the intended action/target. Explicit actions on identified existing servers
and explicit/approved installs proceed without extra confirmation. Do not create,
reinstall or start a game to discover what the user meant.
Read-only requirements or health requests proceed as inspection; do not turn an
assessment into an installation question or an unsolicited install.

## Discover requirements

1. Resolve the alias using [module aliases](../../src/server/module_aliases.json)
   and the selected game's guide in [the guide index](../../docs/README.md).
   Record module, version/build, host OS/architecture, owner/tag and config.
2. Use the row in [capability inventory](../../src/server/module_capabilities.json)
   to locate runtime family, platform declarations, support state and provider
   categories. Then inspect the canonical package import surface and its actual
   implementation under [game modules](../../src/gamemodules). Inventory entries,
   missing hooks, null values and skipped checks cannot prove compatibility.
3. Read `get_platform_requirements`, `get_runtime_requirements`,
   `get_container_spec`, `get_provider_requirements`, `configure`, `install`,
   `prestart` and `get_start_command` where present. Follow shared installers,
   scripts, Dockerfiles and requirement includes on the selected path. Separate
   installation-time tooling from the long-running game runtime. Consult the
   [runtime discovery reference](references/runtime-requirements.md) as needed.
4. Inspect existing files, selected executables/versions, storage, mount access,
   complete port/IP claims, game settings, worlds and licenses. For an existing
   tag use `alphagsm <tag> doctor --json`, help and `set --list`; redact secrets.
   If using the Docker wrapper, inspect its route first: forwarded diagnostics
   can start/recreate the manager. That managed behavior needs no separate
   consent; source inspection is useful if the host lacks Docker.
   Before a tag exists, use source/guide inspection instead of creating a probe
   tag. Check Docker CLI/daemon/Compose and local image identity without pulling.
5. Research official upstream docs/releases for the exact version/platform when
   local evidence is incomplete or disagrees. Distinguish documented minima from
   measured capacity; do not invent RAM, disk, Java or library requirements.
   Report unresolved requirements accurately and resolve them before claiming
   readiness; do not invent an approval gate for missing metadata.

Do not run setup/start/update, install scripts, imports of unfamiliar modules,
builds or test runners as dependency probes. Even `make -n` can evaluate shell
expressions. Read the selected implementation first.

## Report and execute

Produce a concise checklist with a row per requirement:

| Requirement | Needed for / installed where | Status | Evidence/source | Next step |
| --- | --- | --- | --- | --- |
| Exact runtime/version, tool/library, image, port, setting, world, AUTH/BYO input or license | setup/start/query/test; host/manager/game container/provider | present / missing / unknown / not applicable | source path or upstream link plus observed version/file/check | reuse / inspect / user input / proposed approved install |

Include mandatory versus optional status and effective engine/family. Prefer the
repository manager and game images; AlphaGSM-managed helpers/images/dependencies
need no additional approval. Ask only for a fresh game installation when not
already explicit/approved, or genuinely new external software such as missing
host Docker/Java. Clarify ambiguous existing-server requests before changing game
state. Continue independent work while any needed reply is pending.

After an approved install, verify the exact executable/version or image identity,
paths and doctor findings before continuing the relevant lifecycle. A dependency
check is not server health. Finish with a runnable plan or exact blockers and
installation decision; use [provision](../alphagsm-server-provision/SKILL.md) and
[health](../alphagsm-health-check/SKILL.md) for actual lifecycle proof.

Example: “Run a TF2 server.” Resolve `tf2` to `teamfortress2`; inspect Linux
installer support, configured SteamCMD and its libraries separately from the
game's Docker family. If TF2 is absent, ask to install it; once approved, its
managed SteamCMD bootstrap and repository image setup proceed without further
gates. If TF2 is installed and the action is vague, clarify intent before changing
it. An assessment-only request instead ends with the requirements report.
