# Wave 1 Canonical Set Rollout Design

**Date:** 2026-04-17

## Goal

Roll the schema-backed canonical `set` system out beyond TF2 to the remaining
game modules that already own native config sync, so AlphaGSM can expose
consistent user-facing keys like `map`, `servername`, `serverpassword`,
`adminpassword`, `rconpassword`, `maxplayers`, `port`, and `queryport` while
still writing each module's real upstream/native storage keys and config files.

## Approved Approach

The approved implementation approach is:

1. Big wave across the existing config-sync modules
2. Use the new shared canonical-key framework already landed in
   `server.settable_keys` and `Server.doset(...)`
3. Add only small shared helpers where formats obviously repeat
4. Expand each module to every safely mappable upstream-native writable key
   that can be verified from the module's current config contract, current
   sync logic, current templates/guides, and any implementation-time upstream
   research

Rejected alternatives:

- Per-module-only rollout with no shared conventions:
  faster initially, but too much naming drift and duplicated secret-handling
- Meta-framework-first rollout:
  too much abstraction risk before enough real modules have proven the shape

## Scope

This design covers only wave 1, not the entire game-module catalog.

Wave 1 includes the remaining modules that already expose
`sync_server_config(...)`:

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
- `wfserver`
- `wreckfestserver`

`teamfortress2` is not part of this wave because it is already the flagship
reference implementation for the canonical `set` flow.

## Definition Of Done

A module is considered complete for this wave only when all of the following
are true:

1. It exposes `setting_schema`
2. Its `setting_schema` covers:
   - every key already listed in `config_sync_keys`
   - any existing native-config-backed key that `checkvalue(...)` already
     supports and that belongs to a stable upstream config surface
   - any additional upstream-native writable key that can be verified safely
     during implementation
3. `checkvalue(...)` accepts the canonical/native key surface claimed by the
   schema
4. `sync_server_config(...)` writes those datastore-backed values into the real
   native config file(s)
5. `list_setting_values(...)` exists when the module can safely enumerate a
   value family such as maps/worlds/scenarios
6. Unit tests prove the schema, value validation, config sync, and value
   discovery behavior
7. User-facing docs/templates are updated if the new schema-backed keys are
   part of the module's normal operator contract

If a candidate key cannot be mapped safely, that key is out of scope rather
than guessed. The implementation should prefer explicit exclusion over a shaky
mapping.

## Non-Goals

This wave does not attempt to:

- convert all `248` game-module files in one pass
- invent a generic per-format framework that hides module-specific config logic
- add heavyweight integration tests for every touched module
- expose guessed upstream keys without module- or upstream-backed evidence
- normalize keys whose semantics are not actually equivalent for a given module

## Architecture

The rollout stays centered on the shared contract already implemented:

- `server.settable_keys.SettingSpec`
- `server.settable_keys.resolve_requested_key(...)`
- `Server.get_setting_schema()`
- `Server.doset(...)` discovery and alias routing

Each wave-1 module should add or expand these module-level integration points:

- `setting_schema`
- `config_sync_keys`
- `checkvalue(...)`
- `sync_server_config(...)`
- `list_setting_values(...)` where safe

The implementation should not create a second generic mapping layer. The
module remains authoritative for:

- which upstream keys are truly writable
- which canonical aliases are valid
- which values are secrets
- how native config files are rewritten
- how map/world/scenario values are validated

Small shared helpers are allowed only when they remove obvious duplication
without obscuring per-module behavior. Examples:

- JSON patch/update helpers
- simple properties-file helpers
- small quoting/escaping helpers
- shared alias conventions for common canonical key families

## Canonical Key Policy

Canonical names are the user-facing CLI contract. Modules resolve those names
to their native storage keys underneath.

Wave 1 should standardize around these canonical families when semantics truly
match:

- `map`
- `servername`
- `serverpassword`
- `adminpassword`
- `rconpassword`
- `maxplayers`
- `port`
- `queryport`

Modules may also expose module-specific canonicals when the upstream config has
a clear stable meaning, such as:

- `worldname`
- `scenarioid`
- `difficulty`
- `gamemode`
- `welcometext`
- `contactemail`

Alias rules:

- `map` may include aliases such as `gamemap`, `startmap`, `level`, `world`,
  `scenario`, or `mission` only when the module's start-content semantics
  genuinely match
- `servername` may include aliases such as `hostname`, `server_name`, or `name`
- `serverpassword` is only for player join/private password semantics
- `adminpassword` is only for admin-only auth distinct from join or query auth
- `rconpassword` is only for remote console or equivalent query/admin control
- `maxplayers` may absorb aliases like `slots`, `max_players`, or `users` only
  when semantics truly match

Secret rules:

- `serverpassword`, `adminpassword`, and `rconpassword` should be marked
  `secret=True`
- a secret key should only be exposed when the module can actually write it to
  the real native config contract

## Module Inventory And Expected Baseline

This table defines the wave-1 baseline from current code. “Baseline required”
means the implementation must cover at least that surface. “Expansion
candidates” are the first places to look for safely mappable additional native
keys during implementation.

| Module | Native format | Baseline required | Expansion candidates |
| --- | --- | --- | --- |
| `arma3server` | CFG/text | `servername` | `map`/`world`, any other stable `server.cfg` values already owned by module paths |
| `armarserver` | JSON | `port`, `queryport`, `maxplayers`, `scenarioid` | `adminpassword`, `bindaddress`, other JSON keys already written in `sync_server_config(...)` |
| `craftopiaserver` | INI | `port`, `maxplayers`, `worldname` | any stable password or bind-address keys already present in `ServerSetting.ini` defaults |
| `minecraft.bedrock` | properties | `port`, `gamemode`, `difficulty`, `levelname`, `maxplayers`, `servername` | additional stable `server.properties` keys if they can be validated safely |
| `minecraft.custom` | properties | `port`, `gamemode`, `difficulty`, `maxplayers` | `levelname` and other standard Java `server.properties` keys where semantics are stable across supported jars |
| `mumbleserver` | INI | `port`, `users`, `database`, `serverpassword`, `welcometext` | additional stable Mumble INI keys only if the module already owns them clearly |
| `rimworldtogetherserver` | JSON | `port` | additional config-backed server identity or password keys only if implementation-time audit confirms stable writable paths |
| `scpslserver` | JSON + text | `contactemail` | `servername`, `queryport`/query shift, query admin password as `rconpassword` or `adminpassword` when semantics are confirmed |
| `sevendaystodie` | XML | `port` | `servername`, `serverpassword`, `maxplayers`, world/map-like keys when XML mapping is explicit and safe |
| `stnserver` | text | `port` | any additional stable `ServerConfig.txt` keys proved by implementation-time audit |
| `wfserver` | CFG/text | `port`, `servername` (`hostname`) | `map` via `startmap`, additional safe autoexec-backed keys |
| `wreckfestserver` | CFG/text | `port` | additional stable `server_config.cfg` keys only when the current module/config contract can own them safely |

Interpretation rules:

- “Baseline required” is mandatory
- “Expansion candidates” are not optional hand-waving; they are the required
  audit surface during implementation
- If an expansion candidate cannot be verified safely, it should be left out and
  the tests/docs should reflect the narrower confirmed surface

## Research Gate For Additional Native Keys

Because the user explicitly chose the broader “B” option, each module in this
wave must get a short implementation-time audit before code changes are
finalized.

An additional upstream-native key may be added only when at least one of these
is true:

1. The current module's `sync_server_config(...)` already writes it directly
2. The current module's native config template or server guide already names it
3. The current module's config file format and defaults in code clearly own it
4. Official or otherwise trustworthy upstream documentation confirms the key and
   its writable semantics during implementation

A key must not be added when:

- its meaning is ambiguous relative to a canonical family
- the server reads it from a runtime surface AlphaGSM does not actually manage
- the module cannot validate or write it deterministically

## Testing Strategy

Verification should happen at three levels.

### 1. Core/shared tests

Only extend shared resolver/server tests if the rollout introduces a new
cross-module rule that the current shared tests do not already cover.

### 2. Per-module unit tests

Every touched wave-1 module should add or update tests that prove:

- `setting_schema` exists and includes the claimed canonical families
- secret flags are correct for password/admin keys
- `checkvalue(...)` accepts the newly supported canonical/native keys
- `sync_server_config(...)` rewrites the real native file correctly
- `list_setting_values(...)` returns safe values when supported
- map/world/scenario validation rejects obviously bad names when validation is
  practical

### 3. Integration tests

This wave should not try to add heavyweight integration coverage for all `12`
modules in one pass.

Integration changes are allowed only when:

- a module already has meaningful integration coverage, and
- adding canonical `set` assertions is cheap and low-risk

Otherwise, the rollout should rely on:

- module unit tests for the new config surface
- existing lifecycle/integration coverage already present in the repo

## Documentation Strategy

Documentation changes should be proportional to operator impact.

Per touched module:

- update the server guide when new canonical `set` behavior is useful to
  operators
- update the server template when newly managed native keys belong in the sample
  config

Wave-level docs:

- update `README.md` only if the overall operator guidance changes in a useful
  general way
- update `DEVELOPERS.md` once for the wave-level contract, not once per module
- add one `changelog.txt` entry for the wave rather than a separate release note
  per module

## Rollout Shape

The user approved “one big wave anyway,” but implementation should still be
executed as a sequence of small batches with checkpoints. The plan should break
the work into batches that are easy to test and review, likely grouped by
config style and validation similarity:

- JSON-backed modules
- properties-backed modules
- INI/text/cfg-backed modules
- XML/text edge cases
- docs/changelog consolidation

This keeps the delivery aligned with the approved single-wave scope while still
reducing regression risk.

## Success Criteria

Wave 1 is successful when:

- the `12` scoped modules expose canonical schema-backed `set` behavior
- every baseline required key is discoverable through `set --list` and
  `set <key> --describe`
- every safely mappable additional native key found during module audit is
  either implemented or explicitly excluded as unsafe
- password/admin secrets are redacted correctly in discovery output
- config sync continues to write the real upstream/native config files
- existing lifecycle behavior remains green
- docs/templates/changelog reflect the user-facing changes
