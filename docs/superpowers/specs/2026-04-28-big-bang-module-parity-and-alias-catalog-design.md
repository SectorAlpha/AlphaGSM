# Big-Bang Module Parity and Alias Catalog Design

**Date:** 2026-04-28

## Goal

Define a repo-wide design for:

- one full feature-parity contract across the game-module catalog
- one canonical identity model for modules
- one central alias catalog instead of alias wrapper files
- one enforceable parity report that distinguishes code-surface completeness
  from real runtime verification

This design intentionally takes the hard path: no permanent second-class module
tiers inside the active AlphaGSM module surface.

## Approved Approach

The approved scope is:

- `big-bang parity`
- parity applies to every canonical game module in the repository
- skipped, disabled, manual-download, and upstream-blocked modules are still in
  scope for eventual parity
- alias modules should stop existing as module files and should instead become
  central routing metadata

Rejected alternatives:

- support-only parity first:
  too easy to leave the long tail permanently inconsistent
- flagship-modules-only parity:
  improves important modules but does not solve the catalog-level problem
- alias wrappers as first-class modules:
  causes confusion in audits, docs, and parity accounting

## Problem

AlphaGSM currently has two overlapping consistency problems.

### 1. Module capabilities are uneven

Some modules have stronger lifecycle, runtime, observability, config-sync, and
test coverage than others. Missing or partial surfaces are currently visible
through a mix of:

- skipped or disabled integration tests
- modules with unimplemented `status(...)`
- hand-maintained audit reports
- docs that are more descriptive than enforceable

This makes it difficult to answer one basic operator question honestly:

"What does it mean for a server module to be complete?"

### 2. Aliases are modeled as Python modules

The repository currently includes alias wrapper files such as:

- `tf2.py`
- `tf2server.py`
- `cs2server.py`
- `risingstorm2vietnam.py`
- `minecraft/DEFAULT.py`
- `terraria/DEFAULT.py`
- `arma3/DEFAULT.py`

Those files work, but they make aliases look like real game modules. That
creates confusion in:

- parity audits
- docs and support matrices
- runtime-contract checks
- module inventory counts
- human code review

The design should separate canonical modules from alias names cleanly.

## Non-Goals

- Solving every upstream blocker inside this design document.
- Keeping alias wrapper files permanently for convenience.
- Treating aliases as parity-bearing modules.
- Lowering the parity bar for blocked or skipped modules.
- Inventing a second, parallel command surface for module discovery.

## Design Principles

### 1. One active module catalog, one end-state contract

If a canonical game module lives in `src/gamemodules/`, it is part of the
eventual full-parity commitment.

### 2. Canonical modules and aliases are different things

Canonical modules are real implementation units. Aliases are routing metadata.
They should not both live in the same conceptual bucket.

### 3. One user-facing string must have one meaning

A name such as `tf2` or `teamfortress2` must resolve deterministically to one
canonical module id.

### 4. Values in the alias catalog must end at real modules

Alias values must always point directly to real canonical module ids. No alias
chains, no alias-to-alias indirection, and no synthetic terminal nodes.

### 5. Parity reporting must be generated, not hand-curated

Informal docs can summarize findings, but the authoritative parity view should
come from code and tests.

## Scope Boundary

The big-bang program boundary is:

- every canonical module is on a path to the same contract
- aliases do not count as separate modules
- temporary skips may exist during migration
- permanent incomplete states are not an acceptable end state

If upstream reality makes a current canonical module impossible to support
honestly, the repository must eventually make that explicit by fixing it,
redefining its support model, or removing it from the active canonical surface.

## Canonical Module Contract

Each canonical module should eventually satisfy the same repo-wide contract.

### 1. Identity

- exactly one canonical module id
- aliases resolved before import
- persisted server data normalized to the canonical id

### 2. Lifecycle

- `create`
- `setup`
- `install`
- `start`
- `restart`
- `stop`
- `kill`
- clean shutdown verification where applicable

### 3. Observability

- meaningful `status(...)`
- working `query`
- working `info`
- working `info --json` where the shared surface supports it

### 4. Configuration

- validated `set`
- schema-backed discovery where practical
- config sync for real server-owned settings
- practical validation for map/world/level-style values where feasible

### 5. Runtime

- explicit process start contract
- explicit Docker runtime hooks where the module is container-capable
- consistent runtime-family classification where Docker applies

### 6. Operator Safety

- `doctor`
- correct port-claim behavior
- actionable startup and runtime errors
- consistent preflight behavior

### 7. Data Safety

- `backup`
- `restore`
- `wipe`
- explicit and documented behavior for each

### 8. Documentation

- one honest server guide
- one support-state classification
- one config-template path where applicable

### 9. Verification

- unit coverage
- at least one AlphaGSM-driven integration path
- smoke coverage for release-facing supported surfaces

## Parity Status Levels

Parity reporting should distinguish between two different truths:

### `contract-complete`

The module implements the required repo-wide surface correctly according to
static and unit-level contract checks.

### `runtime-verified`

The module has passed the real end-to-end lifecycle through the documented
supported path, such as integration, smoke, or backend runtime validation.

This distinction prevents code-surface presence from being mistaken for
operator-ready support.

## Alias and Resolution Architecture

Alias handling should move into a dedicated core subsystem.

### Files

- `src/server/module_aliases.json`
  central alias and namespace-default data
- `src/server/module_catalog.py`
  typed loader, validator, and resolver
- `src/server/server.py`
  consume shared resolution
- `src/server/port_manager.py`
  consume shared resolution

### Proposed JSON shape

```json
{
  "aliases": {
    "tf2": "teamfortress2",
    "tf2server": "teamfortress2",
    "cs2server": "counterstrike2",
    "risingstorm2vietnam": "rs2server"
  },
  "namespace_defaults": {
    "minecraft": "minecraft.vanilla",
    "terraria": "terraria.vanilla",
    "arma3": "arma3.vanilla"
  }
}
```

### Resolution flow

1. normalize the user-supplied module name
2. resolve alias or namespace default
3. return the canonical module id
4. import only the canonical module
5. persist only the canonical module id

### Expected behavior

These should all resolve to the same canonical module before import:

- `tf2`
- `tf2server`
- `teamfortress2`

Likewise:

- `minecraft` resolves to `minecraft.vanilla`
- `terraria` resolves to `terraria.vanilla`
- `arma3` resolves to `arma3.vanilla`

## Alias Catalog Integrity Rules

The alias catalog should be validated aggressively in CI and at load time.

### Required invariants

- every alias key lives in the same global namespace as canonical module ids
- every alias value must be a real canonical module id that exists on disk as a
  real game module
- alias values must not point to another alias
- alias values must not point to a namespace default
- alias chains are invalid
- alias cycles are invalid
- namespace default targets must also be real canonical module ids

### Name-collision rule

If an alias key is also the name of a real module, both must resolve to the
same canonical module id.

If they do not, catalog validation must hard-fail.

This guarantees one user-facing string has one meaning.

### Practical consequence

Valid:

- `tf2 -> teamfortress2`
- `tf2server -> teamfortress2`

Invalid:

- `tf2 -> tf2server -> teamfortress2`
- `minecraft -> minecraft.DEFAULT -> minecraft.vanilla`
- `alias_name -> missing_module`

## Compatibility and Persistence Rules

The system should preserve compatibility for existing saved servers while
normalizing the stored state.

### Compatibility rule

If an existing datastore contains an alias such as:

- `tf2`
- `tf2server`
- `cs2server`

AlphaGSM should resolve that value to the canonical module id and rewrite the
stored value automatically during load or the next successful command path.

### Persistence rule

Once the catalog is live, new server data should persist canonical ids only.

## Migration Plan

Migration should happen in a strict order.

### Phase 1: add the shared catalog

- add `module_aliases.json`
- add `module_catalog.py`
- keep existing alias wrapper files temporarily

### Phase 2: validate the namespace

Add CI validation that fails when:

- alias targets are not real modules
- alias chains or cycles exist
- alias keys shadow real module names with a different canonical resolution
- namespace default targets are not real modules
- duplicate or ambiguous names exist

### Phase 3: switch all resolution to the shared catalog

At minimum:

- `server.py`
- `port_manager.py`
- parity tooling
- docs and inventory generators that care about module identity

### Phase 4: normalize persisted data

- resolve old alias values from saved server data
- rewrite them to canonical ids

### Phase 5: generate docs and audits from canonical data

- alias docs and alias inventory should read from the catalog
- parity reporting should count canonical modules only

### Phase 6: remove wrapper alias modules

After runtime resolution, compatibility migration, and parity tooling all use
the catalog, delete wrapper files such as:

- `src/gamemodules/tf2.py`
- `src/gamemodules/tf2server.py`
- `src/gamemodules/cs2server.py`
- `src/gamemodules/risingstorm2vietnam.py`
- `src/gamemodules/*/DEFAULT.py` alias shims where catalog defaults replace them

## Verification Model

The repo should verify parity at three levels.

### 1. Catalog validation

Validate:

- aliases
- namespace defaults
- canonical ids
- collision rules
- no alias chains
- no alias cycles
- all targets are real modules

### 2. Contract validation

Audit each canonical module for required surfaces such as:

- lifecycle hooks
- observability hooks
- config contract
- backup/restore/wipe behavior
- docs presence
- runtime metadata where applicable

### 3. Runtime validation

Use the existing test families to prove real behavior:

- unit tests
- integration tests
- smoke tests
- backend Docker/runtime-family tests

## Parity Reporting

Replace scattered hand-maintained audits with one generated parity artifact.

Recommended outputs:

- `docs/module_parity_report.md`
- `docs/module_parity_report.json`

Each row should represent one canonical module and include:

- canonical id
- aliases
- support state
- `contract-complete` status
- `runtime-verified` status
- missing surfaces
- blocker reason if incomplete
- docs presence
- config-template presence
- test coverage presence

### Reporting rule

Alias names must not appear as independent parity-bearing modules.

Alias verification is separate and only proves that name resolution and
backward compatibility behave correctly.

## CI and Release Enforcement

CI should fail if:

- the alias catalog becomes invalid
- a canonical module regresses from complete to incomplete
- parity reporting is stale relative to code

The release process should treat:

- unimplemented `status(...)`
- missing contract surfaces
- invalid runtime metadata
- unresolved alias ambiguity

as parity failures rather than as informal documentation findings.

## Operational Consequences

This design makes the project story clearer:

- one canonical module catalog
- one alias-routing layer
- one parity contract
- one generated truth source for completeness

It also makes it harder to hide long-tail inconsistency behind alias files,
stale docs, or informal audit notes.

## Summary

The repository should move from:

- wrapper alias modules
- mixed parity expectations
- hand-maintained audit notes

to:

- canonical modules only
- central alias metadata
- strict namespace validation
- generated parity reporting
- one big-bang end-state contract for the full catalog
