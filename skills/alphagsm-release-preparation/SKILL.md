---
name: alphagsm-release-preparation
description: "Use when preparing validated AlphaGSM versions, standalone binaries, checksums or release workflow changes."
---

# Prepare a release

Inspect build helper requirements before execution and follow the [approval gates](../alphagsm-server-requirements/references/approval-gates.md) for missing build tools, venv packages and image dependencies. Preparing a release does not authorize a new package installation. Use existing verified tools or wait for approval of the exact build-environment plan.

Inspect [release workflow](../../.github/workflows/release.yml), [binary workflow](../../.github/workflows/binary.yml), [standalone guide](../../docs/standalone-binaries.md), [build script](../../scripts/build_binary.py) and [signing script](../../scripts/sign_release.py). Establish requested version, platforms, artifact destination and whether publishing/tagging was explicitly requested. Preparation alone does not authorize a public release.

Read script help and workflow inputs before building. Run pinned dependencies/quality gates and applicable binary verification/release-gate tests. Keep artifacts paired with real SHA-256 files and required provenance/signing evidence; do not invent a checksum or say an untested binary is validated.

The release workflow publishes on version-tag pushes. Manual dispatch prepares validated builds without publishing; verify actual workflow semantics before triggering it. A requested code/packaging PR stays a PR until the user authorizes the publish action. Do not push a tag as a convenient build trigger for a preparation-only task.

Example: “Prepare vX.Y.Z binaries for review” produces or validates the requested platform artifacts, checksums, test results and release notes. Missing build platform/signing credentials are specific limitations; other platforms remain independently actionable.

Use [changelog-discipline](../changelog-discipline/SKILL.md), keep user docs simple and technical packaging details in DEVELOPERS. Report exact revision/version, artifact paths, executed verification, unavailable checks and publication state. When publication is requested, make the prepared result concrete before any needed final approval; follow existing authorization without repeated confirmation.
