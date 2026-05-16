# AlphaGSM Skills

This directory contains repo-local skills for agents and automation.

Each skill lives in its own directory and exposes a `SKILL.md` file.

## Current Skills

- [changelog-discipline](changelog-discipline/SKILL.md)
- [disabled-server-gate](disabled-server-gate/SKILL.md)
- [install-layout](install-layout/SKILL.md)
- [server-info-gathering](server-info-gathering/SKILL.md)
- [server-lifecycle](server-lifecycle/SKILL.md)
- [smoke-driven-docs](smoke-driven-docs/SKILL.md)
- [system-install-validation](system-install-validation/SKILL.md)
- [wiki-publishing](wiki-publishing/SKILL.md)

## Related Files

- [../AGENTS.md](../AGENTS.md)
- [../SKILLS.md](../SKILLS.md)

## Repository Conventions

Repo-local skills should follow the same core repository conventions captured in
[../AGENTS.md](../AGENTS.md), especially:

- canonical game modules may be flat files or package-backed directories
- package-backed modules should keep checked-in curated manifests beside their implementation
- curated mod/plugin/addon guidance should prefer popular families with authoritative release assets and explicit dependency wiring
