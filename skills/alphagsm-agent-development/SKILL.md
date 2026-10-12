---
name: alphagsm-agent-development
description: "Use when asked to implement, fix or maintain AlphaGSM through a verified repository change."
---

# Develop AlphaGSM

Read [AGENTS.md](../../AGENTS.md), inspect the checkout/diff, and identify the requested deliverable. Preserve unrelated work. For a new PR on latest mainline, determine the actual remote default branch and use an isolated branch/worktree; do not assume it is named main.

Use existing dependencies for read-only checks and tests. Before any new package, venv dependency, toolchain, image or transitive helper install, follow the [approval gates](../alphagsm-server-requirements/references/approval-gates.md) and wait for the user. Prefer repository container images for game validation; obtain first-use Docker consent. For lifecycle tests, use [server-requirements](../alphagsm-server-requirements/SKILL.md) for the exact game/version and installer environment.

## Select the change workflow

| Change | Specialist |
| --- | --- |
| Add a game | [module-authoring](../alphagsm-module-authoring/SKILL.md) |
| Enable a failing/skipped game | [server-enablement](../alphagsm-server-enablement/SKILL.md) |
| Settings to game config | [config-sync](../alphagsm-config-sync/SKILL.md) |
| Port ownership | [port-claims](../alphagsm-port-claims/SKILL.md) |
| Provider credentials/prerequisites | [provider-requirements](../alphagsm-provider-requirements/SKILL.md) |
| Curated manifests/payloads | [curated-content](../alphagsm-curated-content/SKILL.md) |
| Test/CI failure | [test-triage](../alphagsm-test-triage/SKILL.md) |
| Docker/runtime validation | [runtime-validation](../alphagsm-runtime-validation/SKILL.md) |
| Release artifacts | [release-preparation](../alphagsm-release-preparation/SKILL.md) |
| Agent skills | [skill-maintenance](../alphagsm-skill-maintenance/SKILL.md) |

Use [server-lifecycle](../server-lifecycle/SKILL.md) and [install-layout](../install-layout/SKILL.md) for module contracts. Fix shared root causes before adding one-off module workarounds. Write meaningful regression tests for behavior changes; do not test documentation wording.

## Verification and closure

Run relevant checks from the changed checkout. Lint must be 10.00/10. A unit pass does not establish real lifecycle or Docker support. Name skipped/unavailable checks and their actual prerequisites. Keep timeout failures visible and retain reproduction evidence.

For behavior changes, update the smoke runner first when relevant, then [changelog](../changelog-discipline/SKILL.md), matching guide, README and DEVELOPERS. Enablement also closes trackers and campaign checklists. Review the final diff. If a PR was requested, fetch/rebase onto current default branch, rerun affected checks, push and open the PR with the resulting behavior and validation. Publishing/merging follows the user's scope.

Example: “Fix a TF2 query timeout and make a PR.” Reproduce the protocol failure, use test-triage/info-gathering, prove the corrected AlphaGSM lifecycle, then include diagnostics and checks in the PR.
