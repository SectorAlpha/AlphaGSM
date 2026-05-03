# Game Module Config Reuse Design

**Date:** 2026-04-17

## Goal

Define a safe, repo-wide strategy for reusing identical game-module config
surfaces before we move on to broader lifecycle and runtime reuse.

For this phase, "config surface" means:

- `setting_schema`
- `config_sync_keys`
- `sync_server_config(...)`
- low-level config-writer helpers when they are truly the same mechanism

The design should prefer proven reuse over speculative frameworks.

## Approved Approach

The approved sequence is:

1. config reuse
2. lifecycle reuse
3. runtime reuse

Within the config phase:

1. keep existing shared families that already work
2. extract new shared helpers only where the current handwritten surfaces are
   actually identical
3. treat "same top-level key names" as insufficient evidence for sharing if the
   on-disk format or sync semantics differ
4. prefer small family-specific helpers over one generic config meta-framework

Rejected alternatives:

- global config abstraction first:
  too much risk of flattening module-specific file semantics
- per-module-only cleanup:
  misses clear duplication that is already costing review and maintenance time

## Scope

This design covers the config phase only.

It does not yet change the general lifecycle contract or Docker/runtime
wrappers. Those are follow-on phases once the config families are stable.

## Current Inventory

Current modules with explicit config-sync ownership:

- `arma3server`
- `armarserver`
- `craftopiaserver`
- `minecraft.bedrock`
- `minecraft.custom`
- `mumbleserver`
- `rimworldtogetherserver`
- `scpslserver`
- `sevendaystodie`
- `stnserver`
- `teamfortress2`
- `wfserver`
- `wreckfestserver`

Current repo-wide shared family already in place:

- `utils.valve_server.define_valve_server_module(...)`
  This already centralizes config schema and config sync for 40 Valve-family
  modules.

## Findings From The Config Audit

### 1. Valve-family config reuse already exists and should remain the model

`define_valve_server_module(...)` already owns a real shared config family:

- shared `setting_schema`
- shared `config_sync_keys`
- shared `sync_server_config(...)`
- shared config writer logic

This is the reference pattern for "reuse only when the modules genuinely share
the same config contract."

### 2. The Minecraft properties pair is the only handwritten identical schema family

`minecraft.bedrock` and `minecraft.custom` currently share:

- the same `config_sync_keys`
- the same canonical key families
- the same alias family for `map`
- the same datastore-backed property set:
  `port`, `gamemode`, `difficulty`, `levelname`, `maxplayers`, `servername`

Their difference is not the managed config surface itself, but the final native
property mapping for the public server name:

- Bedrock writes `server-name`
- Java properties writes `motd`

This is still a strong shared-family fit because the underlying managed data
contract is the same and only one emitted native property key varies.

### 3. Several modules look similar at a glance but are not the same config family

Examples:

- `sevendaystodie` rewrites XML
- `wreckfestserver` rewrites a CFG line with regex
- `stnserver` rewrites a simple text file from scratch
- `rimworldtogetherserver` patches two JSON files

These all expose `config_sync_keys = ("port",)` but they do not share the same
native config format or the same sync path. They should not be forced into one
config abstraction during this phase.

### 4. There is a second config-level reuse seam in config-writer helpers

Several modules repeat nearly the same "rewrite a simple key/value file while
preserving unknown lines" helper. Today this exists in at least:

- `minecraft.custom`
- `teamfortress2`
- `counterstrike2`
- `counterstrikeglobaloffensive`
- `utils.valve_server`

This is a real reuse opportunity, but it is lower-level than the Minecraft
family work and should be a second config wave rather than the first.

## Design

### Reuse Policy

A config helper may be shared only when all of the following are true:

1. the datastore-backed config meaning is the same
2. the canonical key family is the same
3. the on-disk format behavior is the same
4. the write semantics are the same
5. tests can prove the shared contract without weakening module-specific checks

If any of those fail, keep the logic module-specific.

### Config Families

The config phase should explicitly recognize three categories:

1. existing shared families
2. new shared families
3. intentionally module-specific surfaces

#### Existing shared family

- Valve-family modules through `define_valve_server_module(...)`

#### New shared family for this phase

- Minecraft properties modules:
  `minecraft.bedrock` and `minecraft.custom`

#### Intentionally module-specific for now

- JSON patch modules
- XML rewrite modules
- text-from-scratch modules
- regex-patch modules
- INI/configparser modules

### Minecraft Properties Family

Create a small shared helper surface for the Minecraft properties-backed pair.

That shared surface should own:

- a shared `config_sync_keys` constant
- reusable `SettingSpec` builders for the common managed keys
- a shared schema builder for the properties-backed Minecraft contract
- a shared helper that builds the common `server.properties` payload

The shared payload builder should accept the one real family difference:

- which native property receives the user-facing `servername` value

Expected result:

- Bedrock remains explicit about `server-name`
- Custom/Java remains explicit about `motd`
- the repeated schema and payload boilerplate disappears

This should be implemented in a small Minecraft-scoped helper, not as a
cross-repo config framework.

### Writer Helper Wave

After the Minecraft family lands, the next config wave should unify repeated
simple key/value config writers.

That shared helper should support:

- configurable line matcher pattern
- configurable separator for emitted lines such as `=` or a space
- preservation of unknown lines
- deterministic append of newly managed keys
- UTF-8-safe reads and writes by default

This wave should only adopt modules that already match that behavior exactly.
It should not absorb JSON, XML, `configparser`, or regex-rewrite modules.

## Architecture Boundaries

To keep the design reviewable, shared config code should live at the narrowest
useful scope:

- Valve helpers stay in `utils.valve_server`
- Minecraft properties helpers should live under the Minecraft module family
- general-purpose simple key/value writer helpers may live in a shared utility
  location only after at least two non-Valve families use them cleanly

Do not add a global "config framework" object that tries to encode every file
format AlphaGSM supports.

## Rollout Plan

### Phase A: Preserve the existing shared Valve family

- do not rewrite `define_valve_server_module(...)`
- use it as the reference model for future family extraction

### Phase B: Extract the Minecraft properties family

- refactor `minecraft.bedrock`
- refactor `minecraft.custom`
- add focused unit coverage proving the shared schema contract and the single
  differing native name mapping

### Phase C: Consolidate repeated key/value config writers

- identify the exact-compatible writer implementations
- replace handwritten duplicates with one shared helper
- keep quoting and format-specific behavior explicit where needed

### Phase D: Re-audit remaining module-specific config surfaces

- confirm which modules should stay module-specific
- defer broader reuse until lifecycle and runtime phases

## Testing Strategy

The config phase should be test-led and should preserve per-module confidence.

Required coverage for any extracted config family:

1. unit tests for the shared helper surface
2. updated module-level tests proving the module still exposes the expected
   schema and sync behavior
3. no reduction in assertions around native output keys or config file content

For the Minecraft family specifically, tests should prove:

- identical managed schema shape for both modules
- shared alias handling for `map`
- shared config payload coverage for the common keys
- Bedrock still writes `server-name`
- Custom still writes `motd`

For the writer-helper wave, tests should prove:

- existing lines are preserved
- managed keys are updated in place
- missing managed keys are appended
- separator and quoting behavior remain correct for each adopted caller

## Non-Goals

This design does not attempt to:

- refactor every module with `config_sync_keys = ("port",)` into one helper
- merge JSON, XML, INI, CFG, and properties writers into one abstraction
- change lifecycle hooks such as `configure(...)`, `install(...)`, or `prestart(...)`
- change runtime/container wrappers yet
- hide module-specific native config semantics behind generic names when the
  formats are not actually equivalent

## Definition Of Done

The config phase is successful when:

1. existing shared config families remain explicit and well tested
2. the Minecraft properties pair uses a shared family helper instead of
   duplicated handwritten schema/payload code
3. repeated simple key/value config writers are consolidated only where their
   behavior is actually identical
4. module-specific config surfaces remain module-specific when formats or
   semantics differ
5. the repo is in a stronger position to start the later lifecycle-reuse phase
   without carrying avoidable config duplication forward
