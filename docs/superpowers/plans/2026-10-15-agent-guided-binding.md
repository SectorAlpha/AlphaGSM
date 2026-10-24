# Agent guided binding implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development for the
> cohesive CLI implementation, with test-driven-development and independent review.

**Goal:** Make the common Sector Alpha connection and binding require a short command.

**Architecture:** Keep durable private Config and the existing wire schema. Add
focused local binding/discovery helpers; the CLI offers a guided single-server
form and preserves the explicit legacy form. A scoped portal registration route
allocates private bindings without granting publication or management actions.

**Tech stack:** Python 3.10, argparse, standard-library TLS/networking, pytest.

## Task 0: Scoped portal registration

- [x] In the portal `agent-onboarding` worktree, write failing service/API tests
  for idempotent authenticated `/v1/agent/bindings`, capability isolation,
  revocation/MFA gates, empty initial actions, concurrency and quota limits.
- [x] Implement the route, strict schema and deterministic registration service
  without new tables. Allow private unsupported-game snapshots; fail closed on
  public unsupported games. Test publication/history isolation.
- [x] Run unit and PostgreSQL/role tests before the integrated HTTPS agent journey.

## Task 1: Origins, discovery and guided binding

- [x] Write failing tests for `run(['enroll'])` selecting the default without an
  origin prompt and `run(['bind', '*'])` registering inferred local metadata with
  explicit publication/actions consent; preserve real Config writes and rollback.
- [x] Run focused CLI tests to observe missing parser/default behavior.
- [x] Add DEFAULT_ORIGIN, root-slash normalization, focused helpers under
  `src/agent/`, optional parser flags and guided/legacy dispatch.
- [x] Prove `--host` avoids network, discovery rejects untrusted responses,
  cancellation does not modify a prior binding, and no permissions are enabled
  automatically. Run all agent/contract tests before handing back.

## Task 2: Operator docs and real integration

- [x] Update `docs/sector-alpha-agent.md`, README, DEVELOPERS and the changelog,
  starting the guide with `alphagsm agent enroll` / `alphagsm agent bind mymc`.
- [x] Add a real isolated Minecraft integration assertion that binds using local
  metadata inference with explicit public-host override and no new permissions.
- [x] Run agent/protocol smoke, full unit suite and 10.00/10 lint, then the affected
  real Minecraft test, plus PostgreSQL/TLS full setup against the real portal.
  Check binary-package discovery of the new agent modules.

## Task 3: Review and publish

- [x] Request specification and security/quality review of the delta from
  `086ee1c8`; fix findings with red/green tests and rerun affected gates.
- [x] Verify no shared wire/query interface changes, no test artifacts staged,
  and no live account/server configuration changed.
- [x] Commit, push the existing PR branch, update PR #40 description and attach it
  to this chat. Integrate the reviewed portal endpoint into main as previously
  requested. Preserve the pinned AlphaGSM checkout and shared protocol interfaces.

Reviewed implementation committed as 67755f70; portal endpoint merged/pushed as
9b009ba. Fresh checks: 8,810 AlphaGSM unit tests (4 existing skips), 10.00/10 lint,
268 portal unit tests, 121 PostgreSQL integrations (1 opt-in game skip), and the
real isolated Minecraft guided-binding/restart/duplicate test. PR publication is
combined with the user-requested hostname preflight follow-up, now pushed as
76bd02ba. PR #40 is open against master with its final description and attached
to the chat. Final full AlphaGSM units: 8,857 passed, 4 existing skips; lint
10.00/10 and 35 skills validated.
