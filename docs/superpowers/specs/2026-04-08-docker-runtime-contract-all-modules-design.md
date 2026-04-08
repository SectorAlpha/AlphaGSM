# Docker Runtime Contract For All Game Modules

## Goal

Make Docker runtime metadata a first-class, explicit part of every maintained
game server module in AlphaGSM.

Every module under `src/gamemodules/` should expose:

- `get_runtime_requirements(server)`
- `get_container_spec(server)`

This must be true even when the implementation is only a thin wrapper around a
shared helper in `src/utils/` or `src/server/runtime.py`.

## Current State

AlphaGSM now has a working container runtime layer in
`src/server/runtime.py`, plus several family helpers and example modules. At
the time of writing:

- there are 247 game modules under `src/gamemodules/`
- only 19 modules define both Docker hook functions explicitly
- `src/server/runtime.py` currently attaches inferred hook lambdas to modules
  that do not define them via `ensure_runtime_hooks(...)`

That inference is useful as a transition aid, but it does not satisfy the
desired authoring contract because:

- the functions do not exist explicitly in module source
- authors cannot see the Docker surface when reading a module
- skills and static checks cannot enforce the pattern cleanly
- module-level docs drift more easily when the behavior is implicit

## Desired Contract

The permanent contract for maintained modules is:

1. every module imports `server.runtime as runtime_module`
2. every module defines `get_runtime_requirements(server)` in module scope
3. every module defines `get_container_spec(server)` in module scope
4. modules may delegate those functions to shared helpers, but the functions
   must be visible in the module itself
5. `do_stop(...)` should continue to use `runtime_module.send_to_server(...)`
   where a console stop path exists, following the existing `alienarenaserver`
   style

The style target is the existing explicit pattern used in modules such as:

- `src/gamemodules/alienarenaserver.py`
- `src/gamemodules/q2server.py`
- `src/gamemodules/minecraft/custom.py`

## Non-Goals

This change does not require:

- every module to have a fully bespoke Docker image
- immediate removal of runtime inference during the first migration wave
- a per-module integration test that launches Docker directly

This change also does not mean every family gets unique Docker logic. The goal
is explicit module wrappers over shared family helpers, not 247 custom Docker
implementations.

## Approaches Considered

### 1. Keep inferred hooks in `runtime.py` and do not touch most modules

Pros:

- fastest short-term rollout
- least code churn

Cons:

- fails the desired authoring contract
- hides runtime behavior from module readers
- makes skills and static enforcement weak

This is not the recommended end state.

### 2. Add explicit wrappers to every module, backed by shared helper families

Pros:

- satisfies the explicit module contract
- keeps implementations small and consistent
- matches the established pattern from existing modules
- supports static testing and skills cleanly

Cons:

- large repo-wide edit surface
- requires careful family decomposition to avoid duplication

This is the recommended approach.

### 3. Add bespoke runtime logic per module

Pros:

- maximum per-module freedom

Cons:

- high maintenance burden
- drift across modules becomes inevitable
- much slower to review and verify

This should be avoided except for true one-off outliers.

## Recommended Architecture

Use explicit module-level wrappers everywhere, but centralize the actual Docker
spec construction into a small set of shared helper families.

### Family helper layers

The repo should provide shared helper surfaces for these runtime families:

- `java`
  For jar-based Java servers and proxies, including Minecraft family modules.
- `quake-linux`
  For native Linux Quake-family and similar console-driven binaries.
- `service-console`
  For TCP-heavy daemons with interactive console stop behavior such as TS3.
- `simple-tcp`
  For lightweight services that mostly need mounted config/data and published
  ports.
- `steamcmd-linux`
  For Linux-native SteamCMD-installed servers.
- `wine-proton`
  For Windows-only servers running on Linux through Wine or Proton.

Where possible, helper functions should live close to the current shared logic:

- `src/utils/valve_server.py`
- `src/utils/proton.py`
- `src/server/runtime.py`
- new focused helpers under `src/utils/` where the existing logic is too
  generic or too spread out

### Module pattern

Every module should follow this visible pattern:

```python
import server.runtime as runtime_module


def get_runtime_requirements(server):
    return shared_helper_runtime_requirements(server)


def get_container_spec(server):
    return shared_helper_container_spec(server)
```

If the module is simple enough, it may build the small dict inline, as long as
the two functions exist explicitly in source.

### Runtime inference

`src/server/runtime.py` may keep `infer_runtime_requirements(...)`,
`infer_container_spec(...)`, and `ensure_runtime_hooks(...)` temporarily during
the migration to avoid breaking partially migrated trees.

However, the intended end state is:

- inference becomes compatibility-only
- static tests fail if a maintained module relies on inference instead of
  defining explicit wrappers

That lets the runtime stay resilient while the authoring contract becomes
strict.

## Module Decomposition Strategy

This rollout is too large for a single giant implementation batch. It should be
executed as a program of smaller waves.

### Wave 1: contract and guardrails

- define the explicit rule in skills and agent docs
- add a focused skill for Docker runtime wiring
- add a static unit test that fails if any maintained module lacks both
  functions
- classify modules by helper family

### Wave 2: already-shared families

- finish Valve shared modules
- finish Quake-family modules
- finish current Java family modules
- finish TS3, simple service, and Mumble-style modules

These are the lowest-risk edits because they already have strong family
patterns.

### Wave 3: Wine/Proton family

- migrate all modules using `utils.proton.wrap_command(...)`
- keep module-scope wrappers explicit
- route actual Docker metadata/spec construction through `utils.proton`

This is a large but coherent family.

### Wave 4: SteamCMD Linux-native family

- migrate the broad SteamCMD-native module set to explicit wrappers
- extract additional helper functions where a family shape appears repeatedly

### Wave 5: archive/native and outlier modules

- cover archive-installed native servers
- handle modules with unusual layouts or networking quirks
- keep outlier helper count low

## Skill Changes

This should be captured in two places:

### 1. Update `skills/server-lifecycle/SKILL.md`

The lifecycle skill should state that for every maintained game module:

- `get_runtime_requirements(server)` is required
- `get_container_spec(server)` is required
- explicit module-scope wrappers are required even when shared helpers are used
- `import server.runtime as runtime_module` is the default stop/runtime pattern

### 2. Add a new focused skill

Add a new repo-local skill, proposed name:

- `skills/docker-runtime-wiring/SKILL.md`

Its purpose should be:

- when adding or reviewing runtime hooks for a game module
- choose the correct shared runtime family
- define explicit module wrappers
- keep `do_stop(...)` runtime-aware
- add or update unit tests for both the helper family and representative module
  wrappers
- prefer shared helpers over bespoke Docker dicts

This skill should complement `server-lifecycle`, not replace it.

## Testing Strategy

The rollout needs lightweight static enforcement plus representative behavioral
coverage.

### Static contract test

Add a static unit test that walks `src/gamemodules/` and fails when a
maintained module lacks:

- `def get_runtime_requirements(`
- `def get_container_spec(`
- `import server.runtime as runtime_module`

Namespace redirect modules or deliberate compatibility shims may need a small,
explicit allowlist if they are not true runnable modules.

### Helper-level tests

Each shared family helper should have focused unit coverage for:

- runtime family selection
- port mapping
- mounts
- env values
- command transformation where needed

### Representative module tests

Each helper family should keep representative module tests proving:

- explicit wrappers exist
- wrappers return the expected family
- wrappers preserve module-specific env, ports, and command details

This avoids needing hundreds of bespoke Docker behavior tests up front while
still protecting the family contract.

## Risks And Mitigations

### Risk: duplicated Docker logic across modules

Mitigation:

- prefer shared helpers first
- only keep inline dicts for genuinely tiny modules

### Risk: inferred hooks and explicit hooks diverge

Mitigation:

- treat inference as transitional
- make static tests enforce explicit wrappers
- keep helper logic in one place and have wrappers delegate to it

### Risk: modules with unusual ports or startup commands get misclassified

Mitigation:

- start from helper families, but allow module-local overrides inside the
  explicit wrapper functions
- add representative tests for outliers before broad rollout in that family

### Risk: repo churn becomes too large to review safely

Mitigation:

- execute in waves
- keep each wave scoped to one or two families
- add a static contract test early so progress is measurable

## Success Criteria

This design is complete when:

- every maintained game module explicitly defines both Docker hook functions
- every maintained game module imports `server.runtime as runtime_module`
- shared helper families cover the bulk of modules
- a focused Docker runtime wiring skill exists
- static tests enforce the explicit module contract
- the runtime inference path is no longer the normal authoring mechanism

## Recommendation

Proceed with the explicit-wrapper model for every module, backed by shared
family helpers, and add a new `docker-runtime-wiring` skill plus a static
contract test early in the rollout.

That gives AlphaGSM the authoring model you asked for:

- visible module-level Docker hooks everywhere
- the familiar `alienarenaserver` style
- runtime-aware `do_stop(...)`
- shared logic instead of 247 bespoke Docker implementations
