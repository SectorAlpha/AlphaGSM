# Roadmap Backlog Execution Design

Date: 2026-07-07

## Summary

This design covers execution of the remaining non-future items in
`docs/improvement-roadmap.md` as a coordinated backlog program instead of one
oversized mixed change.

The backlog now falls into four practical workstreams:

- active CI/test stabilization
- remaining runtime-contract and process-to-Docker cleanup
- support-state backlog work (`ENABLED (BYO)` / `DISABLED`)
- opportunistic code-health cleanup that should only happen while touching
  nearby files

The execution model should be:

- split the work into small, reviewable workstreams
- use subagents for focused investigation and implementation
- use unit-test-first development for code changes
- use integration and smoke coverage as confirmation, not as the first or only
  safety net
- run integration-test validation only in the GitHub CI environment, not as a
  local verification step

This keeps the repo moving without bundling unrelated server enablement,
runtime, CI, and docs work into one high-risk branch.

## Goals

- Finish the remaining non-future roadmap items without collapsing them into
  one ambiguous “big cleanup”.
- Prioritize the currently red CI gates before lower-priority backlog work.
- Keep Docker-first runtime validation moving forward without regressing the
  existing lifecycle contract.
- Require unit-test-first changes for code edits wherever a unit-test seam is
  practical, so regressions are caught before expensive integration cycles.
- Keep integration-test execution scoped to GitHub CI so local work stays fast,
  reproducible, and aligned with the repository's intended validation path for
  this campaign.
- Use subagents to parallelize independent investigations while keeping each
  workstream tightly scoped.
- Keep tracker, docs, smoke runners, and changelog aligned when support state
  or lifecycle behavior changes.

## Non-Goals

- Do not implement the “Future Feature Ideas” section of the roadmap in this
  campaign.
- Do not bundle unrelated workstreams into a single commit just because they
  share the same broad roadmap document.
- Do not rely on integration tests alone as the primary design feedback loop
  for code changes.
- Do not run integration tests locally as part of this backlog campaign.
- Do not migrate modules to Docker lanes by adding runtime-specific lifecycle
  branching to module code when the runtime layer can absorb the difference.
- Do not force one-shot opportunistic refactors across untouched files merely
  to reduce duplication.

## Current State

At the start of this campaign:

- the PR workflow queue issue has been fixed by canceling superseded PR runs per
  pull request
- the latest `release_v1` GitHub Actions run has progressed past the fast gates
  and is now surfacing real smoke/integration failures
- the roadmap still contains several open maintenance items, but many older
  items listed in the pick-up order are already complete
- the repo has a clear product direction: Docker support should exist broadly,
  process validation should still be checked, and Ubuntu 24.04 is the Linux
  runtime baseline

That means the remaining work is not one bug. It is a backlog of distinct
problem domains that should be executed in order of operational value.

## Recommended Workstreams

### Workstream A: CI Stabilization First

This is the highest-priority workstream.

Scope:

- roadmap item `1.5` (“Triage the broad red integration batches”)
- current red smoke/integration lanes on `release_v1`
- shared test-harness or workflow regressions revealed by those failures

Expected approach:

- sample representative failed jobs rather than react to every red lane at once
- classify each failure into one of:
  - shared regression
  - lane-specific regression
  - known upstream/server-specific failure
  - CI/runtime environment issue
- fix shared causes before touching individual module lanes

This workstream should finish only when the newest red gates are either fixed
or documented as truly independent follow-up items with evidence.

### Workstream B: Runtime Contract Closure

Scope:

- roadmap item `1.2` (remaining host-process integration lane audit)
- roadmap item `2.3` (`btserver` / `valheim` Docker A2S question)
- any remaining process-first tests whose modules already declare Docker runtime
  families

Execution rule:

- prefer runtime-harness and shared-helper fixes over module-specific runtime
  branching
- only change module lifecycle logic when the actual game-server contract
  differs, not merely because Docker launches it

For `btserver` / `valheim`, the output must be an explicit decision backed by
evidence:

- A2S works and remains the contract, or
- A2S does not hold under the supported Docker lane and the tests/smoke/docs
  are honestly realigned to a different readiness/query contract

### Workstream C: Support-State Backlog

Scope:

- roadmap item `3.1` (`ENABLED (BYO)` automation where authoritative downloads
  exist)
- roadmap item `3.2` (re-verify the three `DISABLED` rows)

Execution rule:

- one module or one tiny related batch at a time
- every support-state promotion must update the full repo contract in the same
  change:
  - module install/setup code
  - unit tests
  - integration test
  - smoke runner if lifecycle changed
  - `docs/TEST_STATUS.md`
  - matching server guide
  - `changelog.txt`

This workstream should begin only after Workstream A has stabilized the active
CI picture enough that new enablement work is not buried under unrelated red
gates.

### Workstream D: Opportunistic Code-Health Cleanup

Scope:

- roadmap item `4.4` (unit-test boilerplate dedupe via
  `tests/unit_tests/gamemodules/helpers.py`)

Execution rule:

- never make this its own giant sweep
- only fold it into touched module/unit-test files when a nearby workstream is
  already editing them

This remains valuable, but it is deliberately subordinate to product and CI
work.

## Execution Order

Recommended order:

1. Workstream A: CI stabilization
2. Workstream B: runtime contract closure
3. Workstream C: support-state backlog
4. Workstream D: opportunistic cleanup

Reasoning:

- active red CI gates block confidence in every later change
- runtime-contract closure removes ambiguity from later module promotions
- support-state promotions are expensive and should happen against a stable CI
  baseline
- code-health cleanup should trail the real product work

## TDD and Safety Contract

This campaign should use a stricter-than-usual safety rule:

- every code change should start with or include a focused unit-test change
  whenever a unit seam is available
- integration and smoke tests should confirm behavior after the unit-level
  contract is expressed

### Unit-Test-First Rules

For code edits:

- write or extend a unit test before the implementation change when practical
- keep unit tests focused on the smallest shared helper, routing decision,
  lifecycle builder, parser, classifier, or module hook that captures the bug
- prefer testing shared runtime and test-harness decisions at the unit level
  rather than reproducing everything through full integration first

Examples:

- CI routing or workflow matrix logic -> static/unit tests
- runtime command/mount/port shaping -> unit tests
- integration helper diagnostics or redaction -> unit tests
- module command/spec generation -> per-module coverage tests

### Integration Role

Integration tests still matter, but their role here is:

- validate that AlphaGSM still performs the real lifecycle correctly
- confirm Docker/process behavior through the public command flow
- reveal gaps that unit tests did not model
- run only in GitHub CI for this campaign

They should not be the first place a predictable regression is expressed when a
unit-test seam already exists.

### Local Verification Boundary

Local verification for this campaign should use:

- unit tests
- static tests
- targeted non-integration commands such as lint or focused scripts

It should not use:

- `tests/integration_tests/*`
- `tests/backend_integration_tests/*`
- smoke or integration wrappers whose purpose is to exercise full server
  lifecycle behavior

The CI environment remains the place where full integration coverage proves the
end-to-end contract.

### Acceptable Exceptions

If a failure is only observable through a full server lifecycle and there is no
meaningful unit seam, it is acceptable to investigate through CI/integration
first, but the fix should still add the smallest possible unit or static guard
after root cause is known.

## Subagent Strategy

Subagents should be used, but only where the domains are independent.

Good parallel subagent uses:

- sampling 2-3 unrelated failing CI batches
- auditing remaining process-first integration tests by file group
- researching one support-state module while another subagent investigates a
  different module

Bad parallel subagent uses:

- editing the same workflow or shared helper from multiple subagents at once
- multiple subagents changing the same module family simultaneously
- broad speculative refactors without a classified root cause

Controller responsibilities:

- choose one workstream at a time
- split only the independent pieces of that workstream
- review and integrate subagent findings before opening more fronts

## Documentation and Tracker Contract

Any workstream that changes user-visible support, lifecycle behavior, or CI
expectations must keep repo-facing documentation synchronized.

Minimum update rules:

- behavior change -> smoke runner first when relevant
- then `changelog.txt`
- then matching guide in `docs/servers/`
- then `README.md` / `DEVELOPERS.md` if the public or contributor contract
  changed

For support-state moves:

- `docs/TEST_STATUS.md` must be updated in the same change
- stale “disabled”, “BYO”, or “AUTH” wording must be cleared from the matching
  docs when no longer true

## Acceptance Criteria

This backlog program is complete when:

- all non-future roadmap items are either:
  - completed in repo state, or
  - deliberately left with an evidence-backed note showing why they remain open
- the active CI stabilization item is no longer an unclassified broad red gate
- remaining process-first Docker-capable integration lanes have been audited and
  either migrated or explicitly justified
- the `btserver` / `valheim` A2S question is resolved with code/tests/docs
  aligned to the answer
- support-state promotions or re-verifications have updated tests, tracker,
  docs, and changelog together
- code changes added focused unit-test coverage wherever practical, with
  integration/smoke used as confirmation rather than the only regression net

## Risks and Mitigations

### Risk: backlog scope explodes

Mitigation:

- enforce workstream boundaries
- keep one module or one shared root cause per change

### Risk: integration failures tempt guess-fixes

Mitigation:

- classify representative failures first
- add narrow unit/static guards once root cause is known

### Risk: support-state work hides CI regressions

Mitigation:

- do not start bulk module promotions until Workstream A is stable

### Risk: opportunistic cleanup turns into unrelated refactoring

Mitigation:

- allow code-health cleanup only in files already being touched for primary
  work
