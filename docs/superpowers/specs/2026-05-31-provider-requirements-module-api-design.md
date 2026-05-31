# Provider Requirements Module API Design

Date: 2026-05-31

## Summary

Some AlphaGSM server modules are not blocked by missing binaries or missing
game assets. Instead, they install correctly but still require
provider-controlled prerequisites before `setup` or `start` can succeed.

Examples already present in the repository:

- `tiserver` requires Epic Online Services dedicated-server credentials
- `pathoftitansserver` requires an Alderon auth token
- `gtafivemserver` and `redmserver` require Cfx license/provisioning
- `ut3server` can optionally use OpenSpy advertising credentials

These cases currently use ad hoc datastore keys, docs wording, and fail-fast
messages. This design introduces a shared module API for declaring those
provider-managed prerequisites in a consistent shape.

The goal is to unify provider-backed requirements now, while leaving room for
future SteamCMD authenticated-install support and secret-management work.

## Goals

- Give game modules one shared hook for declaring provider-backed
  prerequisites.
- Support both install-time and start-time prerequisites.
- Produce consistent AlphaGSM fail-fast messaging from shared metadata instead
  of hand-written per-module text.
- Distinguish provider-backed prerequisites from generic BYO assets at the
  module-contract level.
- Introduce a clearer public support state for provider-backed cases:
  `ENABLED (AUTH)`.
- Make the API extensible enough to absorb the future SteamCMD auth-profile
  design without creating a second parallel system.

## Non-Goals

- Implementing a full secret-storage system in this pass.
- Replacing every existing support-state row in one pass.
- Reclassifying every current BYO server in one change.
- Building provider-specific UI flows beyond shared validation and messaging.

## Problem

Today the repository has multiple kinds of provider-managed prerequisites, but
they are represented inconsistently:

- some modules use bespoke datastore keys and inline `ServerError` messages
- some use generic `ENABLED (BYO)` wording that hides the true provider class
- some docs imply owned assets when the real dependency is credentials,
  licensing, or operator provisioning

That inconsistency makes it harder to:

- keep support-state wording accurate
- group similar servers together
- build future shared secret/auth/profile handling
- reason about which prerequisites are install-time versus runtime

## Recommended Approach

Add a shared optional module hook:

```python
def get_provider_requirements(server):
    return [
        {
            "provider": "eos",
            "kind": "credential",
            "keys": ("eos_client_id", "eos_client_secret"),
            "required_for": ("start",),
            "support_category": "provider-auth",
            "summary": "Epic Online Services dedicated-server credentials",
            "actions": (
                "Set eos_client_id and eos_client_secret before starting the server",
            ),
            "docs_slug": "tiserver",
        }
    ]
```

This becomes the canonical declaration point for provider-managed prerequisites.

## Why This Approach

This is the best first step because it:

- keeps module changes declarative
- creates one consistent validation/messaging path
- avoids overcommitting to a full secret framework too early
- composes naturally with the future SteamCMD auth-profile plan

It also lets AlphaGSM distinguish:

- provider authentication
- provider-issued tokens
- provider license keys
- provider-managed provisioning flows

while also supporting a clearer public support-state split.

## Alternatives Considered

### 1. Keep Ad Hoc Module Fields

Continue adding module-specific keys like `eos_client_id` or `auth_token`
without a shared API.

Pros:

- minimal short-term code churn

Cons:

- keeps validation inconsistent
- increases duplicated messaging
- makes future SteamCMD auth integration harder

### 2. Full Secret Framework First

Implement provider requirements, dedicated secret storage, masking, secret
status commands, and injection in one pass.

Pros:

- strong long-term architecture

Cons:

- too large a scope for the immediate problem
- risks blocking useful support-state cleanup behind a broader secret-system
  rollout

### 3. Provider-Specific Helper Families Only

Add separate EOS, Cfx, Alderon, and OpenSpy helpers with no shared contract.

Pros:

- better than pure ad hoc handling

Cons:

- still fragments the model
- pushes the grouping problem forward rather than solving it

## Module API

### Hook Name

```python
def get_provider_requirements(server):
    ...
```

The hook is optional. Modules that do not need provider-managed prerequisites
do not implement it.

### Returned Shape

The hook returns a list of requirement mappings. Each mapping has:

- `provider`
  - stable provider identifier such as `eos`, `alderon`, `cfx`, `openspy`,
    or later `steamcmd`
- `kind`
  - `credential`, `token`, `license`, `provisioning`, or similar
- `keys`
  - datastore keys, staged-file keys, or other module-visible identifiers
    required to satisfy the prerequisite
- `required_for`
  - tuple containing one or more lifecycle phases such as `setup`, `start`,
    `update`
- `support_category`
  - normalized internal category such as `provider-auth`, `provider-token`,
    `provider-license`, `provider-provisioning`
- `summary`
  - short human-readable requirement summary
- `actions`
  - tuple of operator-facing action sentences
- `docs_slug`
  - matching guide name under `docs/servers/`

Optional future fields can be added later, for example:

- `profile`
  - for SteamCMD auth profiles
- `secret_keys`
  - when a later dedicated secret store exists
- `optional`
  - for non-required provider auth such as optional advertising credentials

## Shared Validation Behavior

Shared helpers in `utils.gamemodules.common` should:

- load provider requirements from the module hook
- filter entries by lifecycle phase
- decide whether the declared keys are present
- raise one standardized `ServerError` when they are not

Example helper shape:

```python
validate_provider_requirements(server, phase="start")
```

The formatted error should:

- identify the module
- identify the provider-managed prerequisite class
- say exactly what must be supplied
- include the explicit next actions
- reference the matching server guide

## Support-State Mapping

Publicly, provider-backed prerequisites should map to:

- `ENABLED (AUTH)`

True operator-supplied asset/export/url/service cases should remain:

- `ENABLED (BYO)`

Internally, AlphaGSM should still distinguish these provider support
categories:

- `provider-auth`
- `provider-token`
- `provider-license`
- `provider-provisioning`

This gives users a clearer supported-state split while still preserving the
more precise internal provider classes needed for future automation and auth
features.

## Initial Migration Targets

First wave:

- `tiserver`
  - EOS dedicated-server client ID and secret
- `pathoftitansserver`
  - Alderon host auth token
- `gtafivemserver`
  - Cfx license/provisioning
- `redmserver`
  - Cfx license/provisioning

Second wave candidates:

- `ut3server`
  - optional OpenSpy credentials
- future EOS-backed servers
- future provider-token or provider-license lanes uncovered during backlog work

## Interaction With SteamCMD Auth Profile Design

This API is intentionally designed to absorb the future authenticated SteamCMD
support plan.

A future authenticated-install module entry could look like:

```python
{
    "provider": "steamcmd",
    "kind": "auth-profile",
    "keys": ("steam_auth_profile",),
    "required_for": ("setup", "update"),
    "support_category": "provider-auth",
    "summary": "authenticated SteamCMD install profile",
    "actions": (
        "Log in to an AlphaGSM SteamCMD auth profile before rerunning setup",
    ),
    "docs_slug": "stormworksserver",
}
```

That means we do not need a separate conceptual system later. Provider-backed
requirements and authenticated-install requirements can share the same module
contract, and both can present publicly as `ENABLED (AUTH)` when appropriate.

## Error Handling

Provider-requirement failures should be:

- explicit
- deterministic
- early in the lifecycle

Expected behavior:

- missing install-time provider requirements fail before or during `setup`
  with a clear message
- missing runtime provider requirements fail before launching the server in
  `start`
- optional provider requirements should not block the lifecycle unless the
  module explicitly marks them required

## Testing

The shared API should land with:

- unit tests for the new helper/formatter behavior
- module coverage updates for each migrated server
- tracker/support-state tests if support-category generation changes

At minimum, tests should prove:

- missing required provider keys fail cleanly
- lifecycle phase filtering works
- messages include the provider summary and docs reference
- existing modules without provider requirements are unaffected

## Risks

### 1. Premature Secret-Storage Coupling

If this API assumes a future secret store too early, it may become harder to
use for current datastore-backed modules.

Mitigation:

- keep the first version compatible with ordinary datastore keys
- add secret-specific behavior later without changing the core requirement model

### 2. Overloading ENABLED (BYO)

If public wording remains too generic, users may still conflate provider auth
with BYO asset staging.

Mitigation:

- use the new support categories internally
- render more explicit provider-specific notices and docs

### 3. Optional Versus Required Confusion

Some providers are only needed for specific features, such as advertising.

Mitigation:

- keep `required_for` phase-specific
- allow optional entries later if needed

## Recommendation

Implement the shared `get_provider_requirements(server)` module hook now,
backed by shared validation and messaging helpers.

Migrate the first provider-backed servers onto that hook and classify them
publicly as `ENABLED (AUTH)` before expanding into full secret-management or
authenticated SteamCMD profile support.

This is the smallest clean step that:

- groups similar servers together
- improves accuracy today
- avoids more one-off module logic
- and gives the future SteamCMD auth work a compatible place to plug in
