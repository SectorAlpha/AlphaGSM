# Server Port Manager Design

## Goal

Add a shared AlphaGSM port manager that prevents port collisions across all
server launch modes:

- process runtime (`screen`, `tmux`, `subprocess`)
- Docker runtime

The port manager must:

- reject explicit port changes when the requested port is occupied
- identify when a conflicting port belongs to another AlphaGSM-managed server
- cover optional ports as well as the primary game port
- always perform a strict collision check before `start`
- perform a collision check during `setup`
- auto-shift ports during `setup` only when the port set is still implicit /
  default-owned, not when the user explicitly requested the exact port

## Confirmed Requirements

The following decisions were confirmed during design:

1. A collision is based on `(hosted_ip, port)` and **ignores protocol**.
2. Collision checks apply to both internal and external hosted endpoints.
3. Collision checks are scoped to the same internal or external hosted IP
   rather than treating all ports on all IPs as globally shared.
4. If a bind/listen IP is unspecified, AlphaGSM treats it as a wildcard local
   binding (`0.0.0.0`) for collision purposes.
5. `localhost` / `127.0.0.1` participate in collision checks as real hosted IPs.
6. `set` must reject occupied ports immediately and explain why.
7. `start` must always hard-fail if any claimed port is occupied.
8. `setup` is the only phase allowed to auto-shift.
9. Auto-shift must apply to the **whole claimed port set together** for a
   multi-port server, not one port at a time.
10. If the user explicitly set the port, AlphaGSM must reject the request and
    recommend the nearest free shared offset instead of silently shifting it.

## Current State

AlphaGSM currently has no shared port-ownership layer.

Relevant behavior today:

- `src/server/server.py`
  - `setup()` configures and installs a server without checking host port
    collisions
  - `start()` launches the server without a shared port preflight
  - `doset()` validates values through the game module but does not enforce
    cross-server port ownership
- `src/server/runtime.py`
  - already resolves Docker port metadata via `ports`
  - already knows about many optional port keys through
    `infer_port_definitions(...)`
- many game modules store additional claimed ports explicitly:
  - `queryport`
  - `clientport`
  - `steamport`
  - `filetransferport`
  - `internalport`
  - `rmiport`
  - `sourcetvport`
  - `rawudpport`
  - `updateport`
- some modules claim additional ports **implicitly** through
  `get_query_address(...)` / `get_info_address(...)`, for example a query port
  derived as `port + 1`

Because there is no shared claim model, AlphaGSM can currently accept a
configuration that collides with another managed server or an unmanaged
listener on the same host.

## Approaches Considered

### 1. Live socket checks only

Use real host-level port probes as the only source of truth during `set`,
`setup`, and `start`.

Pros:

- catches unmanaged listeners accurately
- no separate reservation model to maintain

Cons:

- weak user-facing diagnostics for “this belongs to AlphaGSM server X”
- poor fit for pre-start config conflicts when another AlphaGSM server claims a
  port but is not currently running

### 2. AlphaGSM reservation scan only

Scan all AlphaGSM JSON server stores and reject conflicts from the stored
config alone.

Pros:

- excellent managed-server explanations
- catches config conflicts before a process is listening

Cons:

- misses unmanaged listeners
- can become stale when the host reality differs from stored config

### 3. Hybrid reservation + live occupancy check

Recompute both:

- the AlphaGSM-managed claimed port map from all server configs
- the actual host occupancy from live checks

Then merge the results into one conflict report.

Pros:

- catches managed and unmanaged conflicts
- supports strong diagnostics
- matches `set`, `setup`, and `start` use cases
- does not require a long-lived reservation daemon

Cons:

- more code than either single-source approach

This is the recommended approach.

## Recommended Architecture

Add a new shared module:

- `src/server/port_manager.py`

This module becomes the single place that answers:

- what ports a server claims
- whether those claims collide with other AlphaGSM servers
- whether those claims collide with live host listeners
- what shared offset would move the entire claimed set to a free range

### Data Model

The port manager should work with explicit structures rather than ad hoc tuples.

Recommended logical shapes:

- `PortEndpoint`
  - `scope`: `"internal"` or `"external"`
  - `ip`
  - `port`
  - `source_key`
  - `derived`: whether the endpoint came from an implicit hook/runtime
  - `shiftable`: whether the endpoint moves when the owning stored port keys shift
- `PortClaimSet`
  - server name
  - list of internal endpoints
  - list of external endpoints
  - list of stored port keys that form the atomic shift group
- `PortConflict`
  - conflicting endpoint
  - conflict kind: `"managed"` or `"unmanaged"`
  - managed server name when applicable
  - conflict scope: `"internal"` or `"external"`

The implementation does not need to export those exact classes publicly, but
the internal logic should be structured around those concepts.

## Claimed Endpoint Discovery

The port manager must build a server’s claimed port set from multiple sources.

### 1. Stored numeric port keys

Use datastore keys where:

- the key is `port`, or
- the key ends with `port`, and
- the value is numeric

This includes optional ports like `queryport`, `clientport`, `steamport`,
`filetransferport`, `internalport`, `rmiport`, `sourcetvport`, `rawudpport`,
and similar keys.

### 2. Runtime/container metadata

Use runtime metadata from `src/server/runtime.py` when present, especially:

- Docker `ports` entries already resolved into host/container mappings

This covers modules whose external claim surface is clearer in runtime metadata
than in raw datastore keys.

### 3. Local query/info hook endpoints

Use `get_query_address(server)` and `get_info_address(server)` when they claim
additional local ports not already covered by stored keys.

This is required for modules that derive optional ports implicitly, such as
`port + 1`, rather than storing a `queryport` key explicitly.

Only treat a hook-derived endpoint as a claimed local endpoint when:

- the host resolves to a local/wildcard address (`127.0.0.1`, `localhost`,
  `0.0.0.0`), and
- the port is numeric

### 4. Hosted IP derivation

For **internal** endpoints:

- use `bindaddress` when present
- otherwise default to `0.0.0.0`

For **external** endpoints:

- use an explicit external/public field such as `publicip`, `externalip`, or
  `hostip` when present
- otherwise default the external hosted IP to the internal hosted IP

Do **not** treat arbitrary fields like `connect` as a hosted listen IP; those
fields describe a remote peer rather than an owned endpoint.

### 5. IP normalization

Normalize these for collision purposes:

- `localhost` -> `127.0.0.1`
- empty / missing bind -> `0.0.0.0`

The first implementation may stay IPv4-oriented. If IPv6 handling is added
later, it should happen through explicit canonicalization rules rather than
string comparison spread across the codebase.

## Collision Rules

Two endpoints conflict when:

- they are in the same scope (`internal` with `internal`, `external` with
  `external`), and
- they refer to the same numeric port, and
- their hosted IPs overlap

Hosted IP overlap rules:

- exact same IP conflicts
- `0.0.0.0` conflicts with any internal local IP on the same port
- explicit external wildcard rules should mirror the same logic if introduced
  in future metadata

Protocol is intentionally ignored. If one server claims `27015/udp` and
another claims `27015/tcp` on the same hosted IP, that is still a conflict.

## Managed vs Unmanaged Conflict Detection

### Managed conflicts

Scan all other AlphaGSM server JSON files under the existing server datapath:

- `src/server/server.py:DATAPATH`

For each other server:

1. load the datastore
2. instantiate or minimally inspect it safely
3. collect its claimed endpoints
4. compare against the candidate server’s claimed set

Ignore self-conflicts for the same server name.

This scan is what powers user-facing messages like:

`Port 27015 on 0.0.0.0 is already claimed by AlphaGSM server 'tf2-prod'.`

### Unmanaged conflicts

Perform live host occupancy checks for the candidate claimed set.

The initial implementation can use binding attempts / listener probes rather
than process-name discovery. The key outcome is:

- AlphaGSM can say the port is occupied by something else on the host
- AlphaGSM does not need to identify the unmanaged process by name in phase one

This powers messages like:

`Port 27015 on 0.0.0.0 is already in use by another process on this host.`

## Atomic Port Group Shifting

AlphaGSM must treat a server’s claimed port set as one atomic group.

If a multi-port server owns:

- `port = 27015`
- `queryport = 27016`
- `clientport = 27005`

then setup auto-shift must test **one shared offset** against the entire set.

Search order:

- `+1`
- `-1`
- `+2`
- `-2`
- `+3`
- `-3`
- continue outward within a bounded limit

An offset is valid only if **all** claimed endpoints become collision-free
under the same offset.

When a valid offset is found:

- all shiftable stored port keys are rewritten together
- derived endpoints are recomputed from the shifted stored keys
- one warning is printed summarizing the full port-set change

Example:

`Configured ports were occupied. AlphaGSM shifted this server by +1: port 27015->27016, queryport 27016->27017.`

## Explicit vs Implicit Port Ownership

AlphaGSM must distinguish between:

- **explicit user-owned values**
  - user called `set`
  - user supplied a concrete port during setup/configure
- **implicit/default values**
  - module defaulted the port
  - setup/configure filled in the normal default automatically

This distinction controls whether setup may auto-shift.

### Recommended persistence model

Add lightweight metadata to the server datastore for claimed port ownership,
for example:

- `port_claim_policy`
  - per-key ownership such as `{"port": "explicit", "queryport": "default"}`

The exact field name can vary, but the implementation needs a persistent way to
know whether a stored port came from user intent or from default/implicit setup.

## Call-Site Behavior

### `Server.doset(...)`

Before saving a changed port or hosted-IP key:

1. compute the resulting claimed set with the proposed override
2. run managed and live conflict detection
3. if there is a conflict:
   - reject the change with `ServerError`
   - describe the conflicting endpoint(s)
   - say whether the conflict is managed or unmanaged
   - include the conflicting AlphaGSM server name when managed
   - include the first valid whole-set auto-shift recommendation if one exists
4. if there is no conflict:
   - save the new value
   - mark the changed key as explicit in the ownership metadata

This applies to primary and optional ports alike.

### `Server.setup(...)`

The setup path should change order slightly:

1. `configure(...)`
2. sync runtime metadata
3. run port-manager validation and optional auto-shift
4. `install(...)`
5. sync runtime metadata again if needed

Port validation must happen **before** `install(...)` so generated config files
use the final port values.

Behavior:

- if the claimed set is free: continue normally
- if the claimed set collides and the relevant ports are implicit/default:
  - auto-shift the whole set
  - save the shifted values
  - print a warning
  - continue to install
- if the claimed set collides and any relevant port was explicitly requested:
  - fail setup
  - print the recommended shared offset / suggested ports

### `Server.start(...)`

Always run a strict port preflight immediately before `prestart(...)` and
before the runtime launch.

If any claimed endpoint is occupied:

- fail with `ServerError`
- do not auto-shift
- do not start the runtime

This guarantees consistent behavior across process and Docker modes.

## Runtime Interaction

The port manager should be runtime-aware but not runtime-owned.

That means:

- `src/server/runtime.py` remains the source of resolved Docker runtime metadata
- `src/server/port_manager.py` consumes runtime metadata as one input to claim
  discovery
- neither `ProcessRuntime` nor `ContainerRuntime` should implement their own
  port-collision policy independently

All runtime types should pass through the same shared preflight in
`src/server/server.py`.

## Error And Warning Text

The messages should be direct and actionable.

Recommended patterns:

- explicit `set` rejection:
  - `Cannot set queryport to 27016: port 27016 on 0.0.0.0 is already claimed by AlphaGSM server 'css-prod'. Recommended free offset: +2 (queryport 27018).`
- setup auto-shift warning:
  - `Warning: configured ports were occupied. AlphaGSM shifted this server by +1: port 27015->27016, queryport 27016->27017.`
- strict start failure:
  - `Cannot start server: port 27015 on 0.0.0.0 is already in use by another process on this host.`

## Test Strategy

### Unit tests

Add focused unit coverage for:

- claimed endpoint discovery from:
  - stored `*port` keys
  - bindaddress / publicip
  - runtime metadata `ports`
  - derived query/info hooks
- wildcard overlap rules (`0.0.0.0` vs specific local IP)
- managed conflict detection from multiple server datastores
- unmanaged conflict detection via mocked socket/bind probes
- whole-set offset search for multi-port servers
- explicit `set` rejection with recommended shift
- setup auto-shift for default/implicit ports
- start preflight hard-failure

Likely test files:

- new `tests/unit_tests/server/test_port_manager.py`
- additions to `tests/unit_tests/server/test_server.py`
- targeted module tests only where a special bind/public IP field matters

### Integration tests

Add integration coverage that proves:

- setup warns and auto-shifts when a default port set collides
- `set port ...` fails with a recommendation when a managed server already owns
  the port
- `start` fails when an unmanaged listener occupies the configured port
- Docker runtime and process runtime both honor the same preflight behavior

## Non-Goals

This change does not require:

- identifying unmanaged processes by PID or executable name in phase one
- a long-lived reservation daemon
- protocol-specific collision rules
- per-module custom collision logic

## Risks And Mitigations

### Risk: missing derived optional ports

Mitigation:

- include query/info hook-derived endpoints in claim discovery
- keep tests for modules that derive `port + 1` query ports

### Risk: auto-shifting after config files are already written

Mitigation:

- run setup collision handling before `install(...)`

### Risk: over-blocking on externally advertised IPs

Mitigation:

- keep internal and external scopes separate
- only compare collisions within the same scope
- use explicit external/public IP fields when available

### Risk: stale AlphaGSM reservation view

Mitigation:

- combine datastore scan with live host occupancy checks

## Recommendation

Implement a shared hybrid port manager in `src/server/port_manager.py`, wire it
into `doset(...)`, `setup(...)`, and `start(...)`, treat a server’s claimed
ports as one atomic shift group, and keep startup strict across all runtimes.

This gives AlphaGSM:

- clear rejection on explicit port collisions
- clear managed-server diagnostics
- automatic healing for default port clashes during setup
- consistent safety across screen, tmux, subprocess, and Docker launches
