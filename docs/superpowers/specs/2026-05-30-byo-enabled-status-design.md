# Bring-Your-Own Enabled Status Design

Date: 2026-05-30

## Summary

AlphaGSM currently treats bring-your-own asset/config/authentication lanes as
`DISABLED` or `SKIPPED`, even when the module itself is supported and the only
missing piece is operator-supplied content. This design adds a first-class
`ENABLED (BYO)` status so those modules count as enabled/supported while still
communicating that AlphaGSM cannot fully self-provision them.

## Goals

- Count bring-your-own lanes as enabled/supported in repository trackers.
- Preserve a visible distinction between:
  - fully self-provisioning validated servers
  - supported servers that require user-supplied assets, config, entitlement,
    or install paths
- Show explicit console guidance when a BYO requirement blocks `setup` or
  `start`.
- Keep existing integration-passing semantics for the current `PASSED` state.
- Avoid widening shared runtime/image changes unless the requirement is truly
  family-wide.

## Non-Goals

- Reclassifying genuinely broken or unsupported servers as enabled.
- Removing integration coverage expectations for self-provisioning modules.
- Solving every BYO lane in one PR; the first pass can add the status model and
  migrate the already-proven BYO cases incrementally.

## Recommended Status Model

Repository status states become:

- `PASSED`
  - Full AlphaGSM lifecycle is proven by integration testing.
  - Server is self-provisioning enough for automated lifecycle validation.
- `ENABLED (BYO)`
  - Module is supported and should count as enabled/supported.
  - AlphaGSM lifecycle/config/runtime wiring is considered valid.
  - Operator must still supply required assets, config, credentials, or a
    direct download URL before the server can complete setup/start.
- `DISABLED`
  - Known broken, dead upstream, unsupported platform/binary, or otherwise not
    currently supportable.
- `SKIPPED`
  - Temporary engineering backlog where the module is not yet classified as
    fully supported or disabled.

## Counting Rules

Headline support counts should treat both `PASSED` and `ENABLED (BYO)` as
enabled/supported.

Recommended summary presentation:

- `PASSED`
- `ENABLED (BYO)`
- `DISABLED`
- `SKIPPED`
- Optional derived line in docs or generator output:
  - `SUPPORTED = PASSED + ENABLED (BYO)`

`docs/game-server-support.md` should show `ENABLED (BYO)` modules as checked
supported items, with a short BYO note where useful.

## Console/User Experience

When a BYO requirement blocks progress, AlphaGSM should print an explicit
operator-facing message rather than a vague failure.

Message requirements:

- Say that the server is supported in `ENABLED (BYO)` mode.
- State exactly what the operator must provide.
- State exactly where it must be placed or which setting must be set.
- Keep the message module-specific and actionable.

Examples:

- `cod2server`
  - copy `localized_*.iwd` and `default_localize_mp.cfg` into
    `<install_dir>/main/`
- `minecraft.custom`
  - place the jar at `<install_dir>/<exe_name>` and set `exe_name`
- `dstserver`
  - place `cluster_token.txt` and cluster config under the resolved cluster
    path

Implementation preference:

- Reuse existing module-specific validation/fail-fast hooks where they already
  exist.
- Add a small shared helper for formatting BYO guidance so messages stay
  consistent.

## Repository Changes

### Tracker and docs

- Update `docs/TEST_STATUS.md` to add an `ENABLED (BYO)` section.
- Update summary counts and explanatory legend.
- Update `docs/game-server-support.md` generation so BYO-enabled modules count
  as supported.
- Keep server guides explicit about what must be supplied by the operator.

### Status source of truth

- Extend the current tracker/generator workflow so BYO-enabled modules are not
  inferred from `disabled_servers.conf`.
- Do not keep BYO-enabled modules in `disabled_servers.conf`, because they are
  no longer disabled.
- Add an explicit repository source of truth for BYO-enabled modules and their
  reason text. Preferred options:
  - a dedicated `enabled_byo_servers.conf`, or
  - a structured data file consumed by the tracker generator

Recommendation: use a dedicated `enabled_byo_servers.conf` mirroring the
existing `disabled_servers.conf` ergonomics:

- `module_name<TAB>reason`

This keeps migration simple and avoids overloading the disabled gate.

### Runtime and commands

- BYO modules should fail early with explicit guidance in `setup` or `start`
  once the module knows the missing operator-supplied requirement.
- Existing modules that already have exact BYO notes should be migrated first:
  - `cod2server`
  - `cod4server`
  - `coduoserver`
  - `dstserver`
  - `minecraft_custom`
  - `mxbikesserver`
  - `qlserver`
  - `rtcwserver`
  - `subnauticaserver`
  - additional already-documented BYO lanes such as `ut3server`,
    `hogwarpserver`, `identityserver`, `aloftserver`, and similar cases once
    their support surface is confirmed

## Migration Rules

A server qualifies for `ENABLED (BYO)` when all of the following are true:

- AlphaGSM module/runtime/config logic is considered supportable.
- The remaining blocker is operator-supplied content, entitlement, config, or
  URL, not an unresolved AlphaGSM defect.
- The required operator action is explicit and documented.

Do not migrate a server to `ENABLED (BYO)` if:

- startup/runtime is still broken after required assets are present
- the Linux/Windows runtime path is still unproven or known-broken
- the blocker remains vague

## Testing and Verification

Required for the status-model PR:

- unit coverage for any new tracker/parser/generator logic
- regeneration/check of `docs/game-server-support.md`
- focused tests for any shared BYO console-guidance helper

Required per migrated module:

- doc update in the matching server guide
- explicit tracker row under `ENABLED (BYO)`
- explicit console-facing BYO message at the relevant lifecycle phase

Integration expectations:

- `PASSED` still requires a passing integration test
- `ENABLED (BYO)` does not require CI automation to supply the proprietary or
  user-owned payload, but it does require that the module's support surface and
  instructions are exact

## Rollout Plan

1. Add `ENABLED (BYO)` to tracker/support-generation logic.
2. Add a BYO source-of-truth file and parser.
3. Update repo docs/legend/count semantics.
4. Add consistent BYO console guidance helper or shared pattern.
5. Migrate the already-proven BYO backlog from `DISABLED` / `SKIPPED`.
6. Follow with incremental module cleanups where wording or fail-fast guidance
   is still vague.

## Open Decision Resolved

`ENABLED (BYO)` counts toward the main enabled/supported total.
