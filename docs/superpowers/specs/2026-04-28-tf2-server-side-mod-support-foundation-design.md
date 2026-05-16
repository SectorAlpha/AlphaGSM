# TF2 Server-Side Mod Support Foundation Design

**Date:** 2026-04-28

## Goal

Define the first AlphaGSM mod-support foundation using Team Fortress 2 as the
initial game module, with a design that is reusable for later games.

The first supported slice should cover:

- server-side TF2 mods only
- curated direct-download packages from trusted upstream sources
- ad-hoc Steam Workshop map ids
- AlphaGSM-managed desired state, install state, and reconciliation

This design intentionally lays groundwork for future releases while keeping the
first supported implementation narrow and honest.

## Approved Product Decisions

The approved decisions for this design are:

- canonical module id stays `teamfortress2`
- TF2 implementation moves from a single file into a package directory
- the first implementation is TF2-first, but built on a reusable shared
  mod-support core
- direct-download mod sources are curated-only
- Steam Workshop map ids may be user-supplied ad hoc
- the UX is hybrid:
  operators use explicit `mod` commands, while AlphaGSM persists desired state
  in normal server data
- `alphagsm mytf2 mod add curated sourcemod` should resolve to
  `sourcemod.stable`
- `alphagsm mytf2 mod add curated sourcemod 1.12` should resolve to
  `sourcemod.1.12`

## Problem

AlphaGSM currently has no first-class model for server-side mods.

That creates several gaps:

- no shared way to declare trusted third-party server-side packages
- no shared way to fetch or verify remote mod archives
- no persistent AlphaGSM-side desired state for mods
- no way to reconcile installed mod content during `setup`, `update`, or
  explicit operator actions
- no clean package structure for a complex module such as TF2 once mod support
  is added

Without a shared model, each future module would be forced to reinvent:

- source trust policy
- archive extraction rules
- file ownership tracking
- install/remove/update behavior
- command UX
- test coverage patterns

## Non-Goals

- client-side content distribution orchestration such as FastDL or CDN setup
- arbitrary direct URL installs in the first release
- arbitrary mod install scripts in the first release
- claiming fully supported TF2 Workshop ingestion before a stable TF2-specific
  path is verified
- solving multi-game mod support in the same release
- supporting gameplay total-conversion forks or client mods as part of this
  initial slice

## Design Principles

### 1. Mods are first-class AlphaGSM state

Desired mod state and installed mod state should live in AlphaGSM server data,
not in ad hoc external files.

### 2. Trust policy must be explicit

Curated web downloads should come only from checked-in trusted registry entries.
Ad-hoc input is allowed only for the narrowly defined Workshop path.

### 3. AlphaGSM only mutates files it owns

Removal and reconciliation should never delete unknown TF2 files merely because
they happen to live under `tf/addons` or `tf/custom`.

### 4. Base server lifecycle remains authoritative

Mods are an additional managed install layer on top of the base TF2 lifecycle,
not a replacement for it.

### 5. One TF2 implementation, reusable shared core

TF2 should prove the model, but shared pieces should not be hard-coded into
`teamfortress2` itself.

### 6. Package modules are now part of the canonical module model

The recent alias-catalog work introduced canonical module ids, but the current
catalog and parity tooling still assume that a canonical module is a flat
`*.py` file. This design extends the model so canonical game modules may also
be package directories.

## High-Level Approach

The approved approach is:

- create one shared mod-support core under `src/server/modsupport/`
- convert `teamfortress2` into a package-backed canonical module
- keep `teamfortress2` as the canonical id and import surface
- use TF2 as the first concrete adopter of the shared mod-support core

Rejected alternatives:

- TF2-only bespoke mod logic:
  faster short term, but would force later games to redo the same plumbing
- global multi-game mod platform before any real adopter:
  too much speculative scope before proving one server
- fully ad-hoc direct downloads:
  weak trust story and poor reproducibility

## TF2 Package Refactor

The current file:

- `src/gamemodules/teamfortress2.py`

should become a package:

- `src/gamemodules/teamfortress2/__init__.py`
- `src/gamemodules/teamfortress2/main.py`
- `src/gamemodules/teamfortress2/mods.py`
- `src/gamemodules/teamfortress2/workshop.py`
- `src/gamemodules/teamfortress2/layout.py`
- `src/gamemodules/teamfortress2/curated_mods.json`

### Responsibilities

`__init__.py`

- exposes the canonical `gamemodules.teamfortress2` module surface
- re-exports the public lifecycle hooks from `main.py`
- keeps the import contract stable for existing callers

`main.py`

- base TF2 lifecycle
- setup/install/start/stop/status/update
- config sync
- runtime hooks
- calls mod reconciliation at the correct lifecycle points

`mods.py`

- `mod` command handling
- desired-state mutation
- install/apply/update/remove orchestration
- TF2-specific validation for curated packages

`workshop.py`

- TF2 Workshop item handling
- TF2-specific validation for workshop ids and installed map references
- engine-assisted or provider-backed Workshop integration boundary

`layout.py`

- known TF2 server paths
- approved writable destinations for managed content
- install ordering rules

`curated_mods.json`

- TF2-specific curated mod families and release entries
- trusted source hosts
- version/channel defaults
- extraction and placement metadata

## Shared Mod-Support Core

The shared core should live in:

- `src/server/modsupport/models.py`
- `src/server/modsupport/registry.py`
- `src/server/modsupport/downloads.py`
- `src/server/modsupport/reconcile.py`
- `src/server/modsupport/ownership.py`
- `src/server/modsupport/errors.py`

Optional later additions:

- `src/server/modsupport/workshop.py`
- `src/server/modsupport/checksums.py`

### Shared Responsibilities

`models.py`

- desired-state records
- curated package family/release records
- installed artifact records
- operation reports and error records

`registry.py`

- load module-specific curated registries
- resolve `family` plus `channel/version` into one canonical artifact
- enforce curated-only behavior for direct-download packages

`downloads.py`

- cache remote archives in AlphaGSM-managed download space
- perform safe downloads
- stage extracted content into temporary directories

`reconcile.py`

- compare desired state to installed state
- install missing packages
- refresh changed packages
- remove no-longer-desired files only when AlphaGSM owns them

`ownership.py`

- track per-artifact installed files
- determine whether a file is AlphaGSM-managed
- support safe uninstall/update behavior

## Canonical Module Catalog Changes

The current `module_catalog` and parity tooling assume that canonical modules
are flat files under `src/gamemodules/`. This will break once `teamfortress2`
becomes a package directory.

The catalog model should be extended so a canonical module can be either:

- a file-backed module such as `src/gamemodules/counterstrike2.py`
- a package-backed module such as `src/gamemodules/teamfortress2/__init__.py`

### Required catalog behavior

- canonical module id remains `teamfortress2`
- package directories with `__init__.py` count as canonical modules
- internal package files such as `main.py`, `mods.py`, `layout.py`, and
  `workshop.py` do not count as canonical modules
- alias validation rules stay unchanged

### Required parity/reporting behavior

- parity inventory must count `teamfortress2` once
- source-path resolution must understand package-backed modules
- static contract checks must inspect the canonical package surface, not treat
  helper submodules as standalone modules

## User-Facing Command Model

The UX should be a hybrid model:

- operators use explicit `mod` commands
- AlphaGSM persists the desired state into server data
- `setup` and `update` reconcile saved desired state automatically

The initial TF2 command family should be implemented as the existing AlphaGSM
command surface plus one module command with sub-actions:

- `mod list`
- `mod add curated <family> [channel_or_version]`
- `mod add workshop <workshop_id>`
- `mod remove <entry_id>`
- `mod apply`
- `mod update`
- `mod doctor`

### Examples

- `alphagsm mytf2 mod add curated sourcemod`
- `alphagsm mytf2 mod add curated sourcemod 1.12`
- `alphagsm mytf2 mod add curated metamod`
- `alphagsm mytf2 mod add workshop 1234567890`

### Lifecycle Rules

- `setup` installs the base TF2 server first, then applies desired mods
- `update` refreshes the base TF2 server, then reconciles desired mods
- `mod apply` is the explicit operator action for applying mod changes outside
  full setup/update
- `start` should not silently install missing mods; it may fail clearly if the
  desired mod state is unapplied or broken

## AlphaGSM Server Data Model

Mod state should be persisted in normal server data, for example:

- `mods.enabled`
- `mods.autoapply`
- `mods.desired.curated`
- `mods.desired.workshop`
- `mods.installed`
- `mods.last_apply`
- `mods.errors`

### Desired State

Curated desired entries should record:

- requested family id
- optional requested channel/version
- canonical resolved package id such as `sourcemod.stable`

Workshop desired entries should record:

- workshop item id
- source type `workshop`

### Installed State

Installed entries should record:

- source type
- canonical resolved package id or workshop id
- installed file list
- install timestamp
- download metadata
- status/error info

### Config Awareness Rules

AlphaGSM itself should be aware of mod state in several places:

- `dump` should expose desired and installed mod state
- `backup` and `restore` should preserve AlphaGSM-managed mod intent
- `doctor` should report mod-state issues
- `status` should be able to surface unapplied or broken desired state

The native TF2 config files remain separate:

- `server.cfg` remains TF2-owned gameplay/server config
- AlphaGSM mod state remains AlphaGSM-owned manager state
- generated TF2 files, if later needed, should be derived outputs rather than
  the source of truth

## Curated Registry Model

Curated direct-download packages should use a structured registry rather than
ad hoc aliases.

Each curated family should declare:

- canonical family id
- default channel/version
- one or more named releases

Each release should declare:

- canonical resolved id such as `sourcemod.stable`
- trusted source URL
- allowed source hostname list
- archive type
- expected target layout
- optional checksum metadata
- install destination rules
- ordering/dependency hints where needed

### Resolution Rules

Examples:

- `sourcemod` resolves to `sourcemod.stable`
- `sourcemod 1.12` resolves to `sourcemod.1.12`
- `metamod` resolves to `metamod.stable`

Curated resolution should be strict:

- unknown family fails
- unknown version key for a known family fails
- ambiguous aliases fail
- direct URLs are rejected in curated mode
- the resolved artifact must come from the checked-in trusted registry only

### Registry Storage

The first release should keep TF2 curated metadata local to the TF2 package in
`curated_mods.json`, while the loader and validation logic remain shared. This
allows future game packages to carry their own curated registries while still
using the same core machinery.

## Direct-Download Trust Rules

Curated direct-download installs should be deterministic and conservative.

### Install flow

1. resolve requested family/version to one canonical trusted artifact
2. download into AlphaGSM-managed cache
3. verify required trust metadata
4. extract into a staging directory
5. validate extracted structure against TF2 rules
6. copy/sync into the TF2 server install
7. record installed files and source metadata

### Trust policy

- curated entries must declare allowed source hostnames
- checksum verification should be used whenever upstream provides stable hashes
- if a curated entry requires a checksum and it is missing or mismatched, the
  install fails
- extraction must reject path traversal or writes outside the server root
- only approved TF2 server-side destinations may be written

Initial approved destinations:

- `tf/addons/`
- `tf/cfg/`
- `tf/maps/`
- `tf/custom/`

Anything attempting to write outside approved destinations should hard-fail.

### Initial trusted upstreams

The first TF2 curated registry should be built around official or project-owned
sources such as:

- `metamodsource.net`
- `sourcemod.net`
- `wiki.alliedmods.net`

The initial implementation should prefer exact curated artifact URLs checked
into the registry instead of HTML scraping.

## Workshop Support Boundary

Workshop support is in scope for the interface and the data model, but the
first release should be more conservative in what it claims as supported.

### Approved input

- numeric workshop item ids only

### Planned behavior

- `mod add workshop <id>` records desired state
- TF2-specific Workshop handling validates the id shape
- AlphaGSM reconciles Workshop desired state through a dedicated Workshop path

### Support honesty

Primary official TF2 setup documentation clearly covers:

- TF2 server installation
- TF2 config paths
- custom maps under `tf/maps`
- common plugins such as MetaMod:Source and SourceMod

However, the official sources reviewed for this design do not clearly document
a first-party TF2 dedicated-server Workshop acquisition flow in the same way
that Valve documents workshop hosting for CS:GO.

Therefore:

- the TF2 command surface for Workshop items should be designed now
- the actual TF2 Workshop provider should be treated as experimental until one
  stable TF2-specific path is verified in real tests

The provider may end up using:

- engine-assisted Workshop references
- a Steam/Workshop fetch backend
- another verified TF2-specific ingestion path

but the design should not commit to a fully supported TF2 Workshop download
mechanism before that path is proven.

## Reconciliation and Ownership

Reconciliation should be stateful rather than best effort.

### Reconcile behavior

- desired state is the source of truth
- installed state records what AlphaGSM actually placed
- `mod apply` compares desired vs installed
- matching items are left alone
- missing items are installed
- changed curated items are refreshed
- no-longer-desired items may be removed only when AlphaGSM owns their files

### Ownership rule

AlphaGSM may delete only files it has recorded as its own.

It must not remove unknown files under:

- `tf/addons`
- `tf/custom`
- `tf/maps`
- `tf/cfg`

merely because desired state has changed.

## TF2 Install Ordering

The TF2 module should apply managed content in a deterministic order:

1. base TF2 install
2. engine-level curated dependencies first, such as `metamod`
3. plugin-layer curated dependencies next, such as `sourcemod`
4. curated content packs or map packs after that
5. Workshop maps last

This ordering gives later releases room for dependency modeling without
redesigning the install pipeline.

## Testing Strategy

The first TF2 mod-support foundation should ship with:

### Unit tests

- curated family/default resolution
- curated version resolution
- registry validation
- safe extraction/path validation
- ownership tracking
- desired-state reconciliation logic

### Integration tests

AlphaGSM CLI-driven tests for:

- `mod add curated`
- `mod list`
- `mod apply`
- `mod remove`
- persisted server data reload behavior

### Smoke tests

Extend the TF2 smoke flow to prove:

- base TF2 setup
- curated addon desired state
- `mod apply`
- server still starts
- `status` still works

If practical, later smoke steps can also verify loaded admin/plugin surfaces
through console commands such as MetaMod or SourceMod version checks.

Workshop smoke coverage should be added only after the TF2-specific Workshop
provider is stable enough to claim support.

## Rollout

### Wave 1: curated TF2 server-side mod support

Support:

- curated direct-download packages from trusted upstreams
- TF2 package refactor
- shared mod-support core
- AlphaGSM persisted desired/install state

Initial focus packages:

- `metamod`
- `sourcemod`

### Wave 2: TF2 Workshop maps

Keep the command surface and data model ready in wave 1, but promote Workshop
to supported only after a verified TF2-specific acquisition path exists.

## Documentation Impact

The eventual implementation should update:

- `docs/servers/teamfortress2.md`
- `DEVELOPERS.md`
- `changelog.txt`
- TF2 smoke and integration coverage docs where relevant

Release notes should distinguish clearly between:

- curated TF2 mod support
- experimental or supported Workshop handling

## References

The design assumptions above were checked against current upstream docs on
2026-04-28:

- Official TF2 Wiki, dedicated server configuration:
  https://wiki.teamfortress.com/wiki/Dedicated_server_configuration
- Official TF2 Wiki, Linux dedicated server:
  https://wiki.teamfortress.com/wiki/Linux_dedicated_server
- Official TF2 Wiki, servers overview:
  https://wiki.teamfortress.com/wiki/Servers
- Valve Developer Community, Source Dedicated Server:
  https://developer.valvesoftware.com/wiki/Source_Dedicated_Server
- Valve Developer Community, dedicated servers list:
  https://developer.valvesoftware.com/wiki/Dedicated_Servers_List
- AlliedModders Wiki, installing SourceMod:
  https://wiki.alliedmods.net/Installing_SourceMod
- AlliedModders Wiki, required SourceMod versions:
  https://wiki.alliedmods.net/Required_Versions_%28SourceMod%29
- MetaMod:Source stable downloads:
  https://www.metamodsource.net/downloads.php?branch=stable

## Summary

This design gives AlphaGSM a clean first mod-support foundation:

- TF2 becomes the first package-backed canonical module
- curated server-side packages become trusted AlphaGSM-managed state
- Workshop support is designed into the surface now, but promoted honestly only
  after the TF2-specific path is verified
- the shared core is reusable for future game modules without forcing future
  releases to start from scratch
