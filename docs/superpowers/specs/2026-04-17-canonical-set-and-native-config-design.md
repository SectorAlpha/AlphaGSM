# Canonical `set` and Native Config Coverage Design

**Date:** 2026-04-17

**Goal:** Keep `alphagsm <server> set ...` as the single write path while adding cross-game canonical setting names, discoverability, and a migration path toward modeling every deterministically manageable upstream config variable for each compatible game server.

## Problem

AlphaGSM currently exposes server settings through per-module `checkvalue(...)` functions and optional `sync_server_config(...)` hooks. That works for module-specific keys, but it creates three problems:

1. The same concept uses different names across games and modules.
   Example: `map`, `startmap`, `level`, `servermap`, and `world` all mean roughly the same thing.
2. Users cannot reliably discover what settings exist for a server.
3. Native game config coverage is inconsistent.
   Some modules only expose a subset of a game's real config surface, and many template files remain AlphaGSM-oriented references instead of authoritative native config examples.

## Non-Goals

- Replacing `set` with a new write command.
- Requiring all modules to migrate in one large breaking change.
- Removing legacy `checkvalue(...)` or `sync_server_config(...)` support during the first rollout.

## Current State

The current write flow is:

1. `Server.doset(...)` parses the key.
2. The key goes either to runtime metadata validation or to `module.checkvalue(...)`.
3. The in-memory datastore is updated.
4. Optional sync hooks run through `config_sync_keys` / `sync_server_config(...)`.

This gives AlphaGSM one central mutation path already. The design should extend that path rather than replace it.

## Design Summary

Add a core canonical-setting layer in front of module validation.

- Users continue using `alphagsm <server> set <key> <value>`.
- Core resolves aliases like `gamemap`, `map`, `level`, and `startmap` to one canonical concept.
- Modules can gradually declare schema metadata for canonical settings.
- Discovery stays attached to `set` through read-only options such as `--list`, `--describe`, and `--values`.
- Legacy modules continue working through `checkvalue(...)` until they are migrated.

## Architecture

### 1. Core canonical key resolver

Add a core resolver that accepts a user key and returns:

- the canonical key name
- the original input alias
- module-specific resolution details when needed
- whether the resolved setting is backed by schema metadata or requires legacy fallback

The resolver should normalize case and common separators so these all resolve consistently:

- `gamemap`
- `game_map`
- `game-map`
- `map`

The resolver must support:

- global aliases shared across many games
- module-specific aliases where a concept differs by engine or game
- unambiguous failure messages when multiple canonical candidates are possible

### 2. Canonical setting registry

Introduce a core registry of canonical concepts. The initial registry should include at least:

- `map`
- `port`
- `queryport`
- `maxplayers`
- `servername`
- `serverpassword`
- `adminpassword`
- `rconpassword`
- `bindaddress`
- `publicip`

The registry is the stable user-facing vocabulary. Modules map their native names onto it instead of inventing new public names for the same idea.

Example alias families:

- `map`: `gamemap`, `startmap`, `level`, `servermap`, `world`
- `servername`: `hostname`, `server_name`, `name`
- `serverpassword`: `password`, `joinpassword`, `serverpass`
- `adminpassword`: `adminpass`, `admin_password`, `adminpwd`
- `rconpassword`: `rconpass`, `rcon_password`

These aliases improve ergonomics immediately, even before full module migration.

### 3. Module setting schema

Add an optional module-level contract, referred to in this design as `setting_schema`.

Each schema entry is keyed by canonical setting name and describes:

- aliases accepted by that module
- value type
- validation function or validator metadata
- whether the setting is secret
- where the setting applies:
  - datastore
  - native config file
  - launch arguments
  - runtime metadata
  - any combination of the above
- native config path and key names when known
- description text
- examples
- allowed values or a provider hook when values are enumerable

Modules without `setting_schema` continue using `checkvalue(...)`.

Modules with partial `setting_schema` use schema-backed handling only for the keys they declare and keep legacy behavior for everything else.

### 4. Native config synchronization

Keep `sync_server_config(...)`, but make it the schema-backed bridge to real config files instead of a one-off hook for a few top-level keys.

For schema-backed modules, the sync path should know:

- which canonical settings map to native files
- which native files are authoritative
- how to write the game's real syntax
- whether the same canonical setting also needs launch-argument updates

This keeps the existing `set` mutation model while making real config ownership explicit.

### 5. Legacy compatibility

Compatibility is mandatory during rollout.

If a resolved canonical key is not schema-backed for the current module:

1. Try any module-specific alias fallback rules.
2. Route to existing `checkvalue(...)`.
3. Preserve current datastore and sync behavior.

Modules without schema metadata must behave exactly as they do today.

## Sensitive Settings

Credentials and admin controls must be first-class canonical settings, not exceptions.

Required canonical secret-like settings:

- `serverpassword`
- `adminpassword`
- `rconpassword`
- `spectatorpassword` where applicable

Schema metadata must include a `secret` flag so discovery output and future inspection paths can redact values by default.

Discovery should still show that these settings exist and what they control, but it must not echo stored secret values in normal output.

## `set` Command UX

`set` remains the single mutation path.

Normal writes:

- `alphagsm mytf2 set gamemap cp_badlands`
- `alphagsm mytf2 set rconpassword hunter2`
- `alphagsm myserver set adminpass secret`

Read-only discovery extensions on the same command:

- `alphagsm mytf2 set --list`
- `alphagsm mytf2 set --list --verbose`
- `alphagsm mytf2 set gamemap --describe`
- `alphagsm mytf2 set gamemap --values`

Resolution order for `set <key> <value>`:

1. Normalize the input key.
2. Resolve the alias to a canonical key.
3. Check whether the module exposes schema metadata for that canonical key.
4. If yes, validate and apply through schema-backed handling.
5. If not, fall back to legacy `checkvalue(...)`.
6. Persist through the same datastore path.
7. Run sync hooks and runtime metadata sync as appropriate.

## Discoverability

Discovery is attached to `set`, not a separate command family.

`set --list` should show:

- canonical key
- accepted aliases
- type
- whether the setting writes to datastore, config, launch args, runtime metadata, or a combination
- whether it is secret

`set <key> --describe` should show:

- description
- aliases
- expected type
- examples
- native target path/key details when known
- whether it syncs to config, launch args, or runtime metadata

`set <key> --values` should show allowed values when the module can enumerate them. This is intended for:

- maps
- worlds
- levels
- branches
- scenarios
- presets

For modules that cannot enumerate allowed values safely, `--values` should return a clear explanation instead of pretending the value space is known.

## Data Ownership Rules

Each schema-backed setting must declare where the source of truth lives.

Supported ownership combinations:

- datastore only
- datastore + native config
- datastore + launch args
- datastore + runtime metadata
- datastore + native config + launch args

The datastore remains AlphaGSM's central representation. Native files and launch args are derived outputs unless a future design explicitly introduces import-from-config behavior.

## Rollout Plan

### Phase 1: Core resolver and discovery

Add:

- canonical key normalization
- alias resolution
- `set --list`
- `set <key> --describe`
- `set <key> --values`

This phase should not require broad module rewrites.

### Phase 2: Flagship schema-backed modules

Migrate a small, representative set first:

- Source-family examples such as TF2, FoF, and DOI
- one secret-heavy example covering `serverpassword`, `adminpassword`, or `rconpassword`
- one native-config-heavy example outside Source

This phase proves:

- canonical aliases work in practice
- secrets redact correctly
- real config files update correctly
- launch-argument-backed settings still behave correctly

### Phase 3: Broad native config expansion

Migrate modules family by family and expand template/doc coverage so native game config files become authoritative rather than partial references.

This phase is where the project moves from "AlphaGSM-managed subset" toward "full native config surface for compatible servers, including the full upstream setting surface wherever AlphaGSM can manage it deterministically."

## Testing Strategy

### Core unit tests

Add unit tests for:

- alias normalization
- canonical resolution
- ambiguous alias failures
- secret redaction
- legacy fallback when no schema exists
- schema-backed routing when metadata exists

### CLI and command behavior tests

Add tests for:

- `set --list`
- `set <key> --describe`
- `set <key> --values`
- normal write flow using canonical and alias keys

### Module tests

For schema-backed modules, test:

- canonical key to native key mapping
- validation behavior
- config sync output
- launch-argument updates
- secret handling

### Integration tests

Add at least one end-to-end integration path for a flagship server that proves:

- `alphagsm mytf2 set gamemap cp_badlands`
- `alphagsm mytf2 set rconpassword secret`
- `alphagsm mytf2 set gamemap --describe`

and confirms the live server config or launch command reflects the change.

## Migration Safety Rules

- `set` remains the only write path.
- Unmigrated modules must preserve current behavior.
- Schema-backed support is additive per module.
- Native config templates and server guides must be updated as modules gain real config ownership.
- Secret settings must be redacted consistently anywhere discovery or inspection output is added.

## Success Criteria

This design is successful when:

- users can set common concepts using canonical names or familiar aliases
- `set` can explain what a server supports without reading module source
- sensitive settings are discoverable but safely redacted
- modules can gradually declare and own the full native config surface for compatible servers
- legacy modules continue working during migration
- flagship migrated modules prove the pattern works across config-file-backed and launch-arg-backed servers

## Chosen Direction

Use a hybrid migration:

- core canonical-key resolver first
- `set`-based discovery built into the same command
- additive module schema contract
- gradual expansion toward full native config coverage

This is the smallest path that gives immediate user value without requiring a breaking rewrite of every game module.
