# Standalone distribution and CI integrity implementation plan

The user authorized these fixes together on PR #36 (`release_v1`), superseding
the previous recommendation to split the frozen integration branch.

**Goal:** Make binary packaging and lifecycle validation independent of the source
checkout, make required CI results trustworthy, and validate before publishing.

**Architecture:** Preserve the shared module/runtime contract. Collect all owned
package resources, test shipped executables through separate CLI invocations,
and keep process supervision alive across invocations. CI records expected jobs
and original execution environments; missing evidence cannot count as a pass.

## Work and acceptance criteria

- [x] CI integrity: extract/test summary logic; reject missing/malformed/empty
  required reports and failed setup jobs; preserve deliberate routing skips.
  Preserve runner class and provider configuration in isolated rechecks; retain
  initial failures and bound retries. Fix Minecraft readiness/shutdown exit codes.
- [x] Packaging: collect package data and dynamic modules (excluding the nonfunctional Factorio placeholder);
  add executable selection to lifecycle harnesses and independent binary
  acceptance coverage. Test manifests without a checkout or Python dependency.
- [x] Supervision: authenticated local control across CLI invocations, graceful
  shutdown and descendant cleanup; verify using independent processes and the
  frozen executable. Preserve existing screen/tmux behavior.
- [x] Releases: explicit platform/architecture matrix, pinned build dependencies,
  reusable validation, one publication job after all validation, provenance and
  signing integration with explicit external prerequisites.
- [x] Updates: same-filesystem staging, rollback, and Windows deferred replacement;
  verify failure paths and version/platform selection.
- [x] CI operations: scheduled broad coverage, merge-group routing, stable required
  gate; keep provider prerequisites and persistent failures visible.
- [x] Docs: changelog, binary support matrix, release/operator setup, developer
  contracts and latest CI evidence. Record external blockers without claiming
  unsupported platforms or unproven game servers passed.
- [ ] Verification: focused regression tests, binary build and acceptance,
  `make lint`, `make test`, CI-only real integration/backend checks; inspect
  final diff and obtain independent review before updating the PR.

Each implementation task adds a failing regression before its fix. Independent
files may be delegated, with workflow integration and final review owned by the
primary agent. Signing credentials, provider provisioning and remote platform
execution require actual external evidence before they can be marked complete.

## Additional approved design work

- [x] Shared generated capability inventory with unknown coverage preserved.
- [x] Serialized CLI state updates and atomic/journaled writes.
- [x] Redacted doctor JSON, CI failure evidence and installation provenance.
- [x] Restore meaningful static checks and fix exposed defects.

User constraint: run integration and real game/backend acceptance in CI only.
Signing identities and provider runner provisioning remain external prerequisites.

## Implementation verification

Implemented items above describe code and test wiring, not a release certification.
Local assembled checks passed 7,588 unit tests (three platform-specific skips),
pylint 10.00/10, actionlint, generated inventory/report freshness, and Linux binary
compilation/version invocation. Final review added downloader and bulk-dispatch
regressions; the assembled unit/lint checks passed again before pushing. Real game acceptance,
Windows-native paths and all remote targets remain pending fresh CI evidence.

## Additional user steering: platform compatibility

- [x] Reject known game-specific OS/CPU incompatibilities before install/start.
- [x] Check native executable format and preserve explicit Wine/Proton wrappers.
- [x] Check Docker daemon OS independently of desktop host OS.
- [ ] Confirm follow-up Windows cache and Docker console/evidence fixes in CI.

Follow-up validation: 7,645 unit tests passed (three platform-specific skips),
with focused coverage added for human-readable platform diagnostics afterward.
First CI passed native binary lifecycle on Linux ARM64 and both macOS targets,
and Linux x86-64 reached successful native lifecycle before its Docker check.
Windows cache replacement and Docker permissions/evidence defects were reproduced
and fixed with unit coverage; fresh CI remains the acceptance gate.
