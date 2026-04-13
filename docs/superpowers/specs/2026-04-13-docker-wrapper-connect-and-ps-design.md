# Docker Wrapper Connect And Ps Design

## Goal

Make `./alphagsm-docker <server> connect` work for Docker-backed servers by
attaching from the host shell to the real game-server container, and add a
wrapper-level `ps` command that lists Docker-launched AlphaGSM servers for the
current wrapper home.

## Scope

This design covers:

- `alphagsm-docker`
- `src/core/main.py`
- unit tests for the wrapper and command parser

This design does not change:

- process-runtime `connect` behaviour
- manager-container lifecycle behaviour
- game-module runtime contracts
- backend integration workflow structure

## Desired Behavior

### Docker wrapper connect

`./alphagsm-docker <server> connect` should no longer be forwarded through the
manager container with `docker compose exec ... python alphagsm ...`.

Instead, the wrapper should:

1. resolve the Docker-backed server from the current `ALPHAGSM_HOME`
2. determine the effective `container_name`
3. verify that the target container exists and is running
4. print a short detach hint
5. run `docker attach <container_name>` directly from the host shell

Detach behaviour should use Docker's native keys:

- `Ctrl-p`
- `Ctrl-q`

### Docker wrapper ps

`./alphagsm-docker ps` should list Docker-backed AlphaGSM servers known to the
current wrapper home.

The command should:

- scan the wrapper-managed server config directory
- include only servers configured for Docker runtime
- display the server name and effective container name
- show whether the container is running, stopped, or missing
- include host port mappings when available

The list should be scoped to the current wrapper home, not every matching
container on the host.

### Reserved server names

`ps` should become a banned server name in the main CLI parser so it cannot
conflict with the new wrapper command.

## Approaches Considered

### Approach 1: Wrapper-native metadata-driven connect and ps

- special-case `connect` in `alphagsm-docker`
- read server metadata from the wrapper's AlphaGSM state
- resolve `container_name` from stored runtime metadata
- add a wrapper-native `ps` command using the same metadata

Pros:

- works with custom `container_name` overrides
- keeps interactive attach on the host where it belongs
- avoids requiring the manager container just to connect or list servers
- keeps results scoped to the current wrapper home

Cons:

- the wrapper needs a small amount of AlphaGSM state-reading logic

### Approach 2: Name-convention-only connect and ps

- assume every container is named `alphagsm-<server>`
- list host containers by name prefix

Pros:

- shortest implementation

Cons:

- breaks for custom `container_name` values
- lists host-wide containers rather than wrapper-scoped servers
- less trustworthy than using AlphaGSM's own stored metadata

### Approach 3: Manager-assisted connect and ps

- ask the manager container for metadata
- attach from the host after manager-side resolution

Pros:

- reuses existing AlphaGSM command paths

Cons:

- adds an unnecessary dependency on the manager being up
- more moving parts for a wrapper-level convenience feature

## Recommended Design

Use Approach 1.

### Server metadata resolution

The wrapper should resolve server information from the current
`ALPHAGSM_HOME/home/conf/<server>.json` store.

For `connect` and `ps`, the wrapper should:

- treat `runtime=docker` as the inclusion rule
- use stored `container_name` when present
- fall back to `alphagsm-<server>` only when no explicit container name exists

This preserves compatibility with the existing runtime contract, where
`container_name` is configurable.

### Connect flow

When the wrapper receives `<server> connect`:

1. do not call the generic `exec_alphagsm` passthrough
2. resolve the server metadata locally
3. fail clearly if the server is unknown or not configured for Docker runtime
4. check the resolved container state with Docker
5. if running, print a short attach banner and call `docker attach`
6. if missing or stopped, exit with a clear message that points the user toward
   `status` or `start`

The wrapper should not try to emulate `screen`/`tmux` detach semantics for
Docker. The intended detach path is Docker's own `Ctrl-p`, `Ctrl-q`.

### Ps flow

When the wrapper receives `ps`:

1. do not treat `ps` as a server name
2. scan the wrapper-managed config directory for server JSON files
3. resolve Docker-backed entries and their effective container names
4. inspect Docker for state and host port mappings
5. print a compact, human-readable listing

If no Docker-backed servers are known in the current wrapper home, the command
should print an empty-state message rather than failing.

### CLI compatibility

Add `ps` to the banned server-name list in `src/core/main.py` alongside the
existing reserved wrapper command names. This prevents a new ambiguity between
wrapper commands and server names.

## Error Handling

- unknown server config: explain that the server is not defined in the current
  `ALPHAGSM_HOME`
- non-Docker server config: explain that wrapper `connect` only attaches to
  Docker-backed servers
- container missing: explain that no matching Docker container exists
- container stopped: explain that the server is not running
- Docker attach failure: surface the failure clearly and preserve the exit code

## Testing Strategy

Update unit tests to cover:

- wrapper `connect` bypasses manager passthrough
- wrapper `connect` resolves explicit `container_name` values
- wrapper `connect` prints the Docker detach hint
- wrapper `connect` fails cleanly for missing, stopped, or non-Docker servers
- wrapper `ps` lists Docker-backed servers from the current wrapper home
- wrapper `ps` ignores non-Docker servers
- `ps` is rejected as a server name by the main CLI parser

This design intentionally keeps the first pass at unit/static coverage. A
backend integration attach test is optional later if it can be added without
making CI flaky.

## Risks And Guardrails

- Reading server metadata in the wrapper duplicates a small amount of runtime
  resolution knowledge. The guardrail is to keep the logic narrow and only rely
  on stable stored keys: `runtime` and `container_name`.
- `docker attach` is inherently interactive. The wrapper should keep its role
  minimal and avoid adding terminal-control behaviour beyond the detach hint.
- `ps` must remain scoped to the wrapper's configured home so it does not
  unexpectedly mix unrelated AlphaGSM environments on the same host.

## Implementation Notes

- keep generic wrapper passthrough behaviour for other AlphaGSM commands
- keep the manager startup path unchanged for non-interactive commands
- prefer concise table-like output for `ps`
- reserve only `ps` for this change; do not introduce extra wrapper aliases in
  the same pass
