# Docker Runtime Wiring

| Field | Value |
| --- | --- |
| Purpose | Keep game-module Docker metadata explicit, reviewable, and aligned with the shared runtime-family builders. |
| Use when | Adding a module, reviewing runtime hooks, or migrating a module to shared Docker helpers. |
| Main source | `src/server/runtime.py`, `src/utils/proton.py`, the relevant game module, and representative unit tests. |

| Field | Value |
| --- | --- |
| Inputs | Runtime-family choice, module datastore values, shared runtime builders, and the module's process launcher. |
| Outputs | Module-scope `get_runtime_requirements(server)` / `get_container_spec(server)` wrappers, plus tests that cover the wrapper surface. |
| Related files | `src/gamemodules/**`, `src/server/runtime.py`, `src/utils/proton.py`, `tests/unit_tests/**`, `tests/backend_integration_tests/**`. |

Use this skill when wiring Docker metadata for a maintained game module.

## Contract

Every maintained game module should make its Docker runtime contract obvious at the top level:

- `import server.runtime as runtime_module`
- `get_runtime_requirements(server)`
- `get_container_spec(server)`

Keep those wrappers in module scope even when they call shared helpers.

## Workflow

1. Choose the runtime family first.
2. Prefer the shared builders in `server.runtime` for native families like `java`, `quake-linux`, `service-console`, `simple-tcp`, and `steamcmd-linux`.
3. For Windows-only modules on Linux, prefer the shared `utils.proton` helpers and the `docker/wine-proton/` scaffold.
4. Keep the module-level wrappers explicit so reviewers can see the runtime contract without chasing inference.
5. Update representative unit tests so they exercise the module wrapper surface, not just the shared helper.
6. Keep Docker backend coverage honest: runtime families belong in `tests/backend_integration_tests/docker_family_matrix.py`, each family should declare three representative cases, and every **active** case must be exercised by `tests/backend_integration_tests/test_backend_docker.py` in CI.

## Pattern

Use explicit module wrappers that delegate to the shared runtime helpers:

```python
import server.runtime as runtime_module


def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(("port", "udp"),),
    )


def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=(("port", "udp"),),
    )
```

When a module uses `utils.proton`, keep the same explicit wrapper pattern and call the proton helpers from module scope.

## Review Checklist

- The runtime family is chosen before any Docker dict is built.
- The module imports `server.runtime as runtime_module` when it uses the shared builders.
- `get_runtime_requirements(server)` and `get_container_spec(server)` exist in module scope.
- Shared helpers are called through explicit wrappers instead of hidden fallback wiring.
- Representative unit tests cover the wrapper functions or the shared helper surface used by the module.
- Active Docker backend cases prove the AlphaGSM lifecycle in CI: `create`, `setup`, `start`, readiness, `status`, `query`, `info`, `info --json`, `stop`, and shutdown verification.
