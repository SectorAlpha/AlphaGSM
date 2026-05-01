# Server Lifecycle

| Field | Value |
| --- | --- |
| Purpose | Preserve, document, and enforce the standard AlphaGSM server lifecycle contract. |
| Use when | Changing lifecycle code, adding a new game server, or documenting per-server behaviour. |
| Main source | `server/server.py`, `server/runtime.py`, `core/main.py`, smoke tests, and the relevant game module. |

| Field | Value |
| --- | --- |
| Inputs | Server dispatch logic, default command contract, and game module lifecycle code. |
| Outputs | Updated lifecycle code, matching docs, matching tests, and command-contract compliance for new modules. |
| Related files | `server/server.py`, `server/runtime.py`, `core/main.py`, `screen/**`, `gamemodules/**`, `tests/server/*`, `tests/smoke_tests/*.sh`. |

Use this skill when changing or documenting the lifecycle for a game server module, especially when adding a new game server type.

## Focus

Understand, preserve, and enforce this standard AlphaGSM flow:

1. `create`
2. optional `set`
3. `setup`
4. `start`
5. readiness verification
6. `status`
7. `message` if supported
8. `stop`
9. shutdown verification

## Standard Command Contract

New game server modules should fit into the standard AlphaGSM command model rather than inventing a separate workflow.

At minimum, a new server type should work correctly with the shared command surface for:

- `create`
- `setup`
- `start`
- `stop`
- `status`
- `query`
- `info`
- `set`
- `connect`
- `restart` (if the server needs custom restart logic)

Where applicable, it should also integrate cleanly with:

- `message`
- `backup`
- `dump`
- `update` (if the server supports in-place updates)


The goal is that a user can create and operate a new server type using the same AlphaGSM mental model they already use for Minecraft, TF2, or CS:GO.

## Game Module Function Contract

Every canonical top-level game module is a package-backed Python module under
`src/gamemodules/<name>/` with `__init__.py` as the import surface. The
`Server` class (in `src/server/server.py`) calls into that canonical module
surface via named attributes. Use this table as a checklist when writing or
reviewing a module.

Flat `.py` files are still fine for helper submodules that live inside an
existing package-backed game family, but top-level user-facing game modules
should now be directories, with the main implementation in `main.py`.

### Required functions — every module must have these

| Function | Signature | Backs command | Notes |
|---|---|---|---|
| `configure` | `(server, ask, *args, **kwargs)` | `setup` | Collect and store config values.  If `ask` is True, prompt the user.  If False, raise `ServerError` when required info is missing.  Returns `(args, kwargs)` to forward to `install`. |
| `install` | `(server, *args, **kwargs)` | `setup` | Download / copy files and write initial config so the server is ready to start. |
| `get_start_command` | `(server, *args, **kwargs)` | `start` | Return `(command_list, working_dir)` — the argv list and the directory to run it in. |
| `do_stop` | `(server, time, *args, **kwargs)` | `stop` | Send a stop command to the running server.  `time` is minutes elapsed since the stop was initiated.  Called repeatedly until the server exits or the timeout (`max_stop_wait`) is reached. |
| `status` | `(server, verbose, *args, **kwargs)` | `status` | Print game-specific status.  Only called when `verbose > 0` — the caller already prints the "running / not running" line. |
| `message` | `(server, message, *args, **kwargs)` | `message` | Send a chat or broadcast message through the server's active console-input pathway. Prefer the runtime-aware helper (`server.runtime.send_to_server(server, ...)`) or a shared wrapper built on it so the same hook works whether the server is reached via screen, tmux/subprocess facade, or Docker exec-console input. If the server has no concept of in-game messages, print a clear explanation and return without raising. |
| `backup` | `(server, *args, **kwargs)` | `backup` | Back up the server.  Call `backup_utils.backup(server.data["dir"], server.data["backup"], profile)` from `utils.backups.backups` in the standard case. |
| `checkvalue` | `(server, key, *values, **kwargs)` | `set` | Validate and convert a value before it is stored.  Return the sanitised value, return the string `"DELETE"` to request deletion, or raise `ServerError` with a clear message for invalid input.  Delegate backup-related keys to `backup_utils.checkdatavalue`. |
| `get_runtime_requirements` | `(server)` | runtime selection | Return runtime metadata for Docker-capable modules.  Preferred families today are `"java"`, `"quake-linux"`, `"service-console"`, `"simple-tcp"`, `"steamcmd-linux"`, and `"wine-proton"`.  Use `{"engine": "docker", "family": "<family>"}` plus fields like `java`, `env`, `mounts`, and `ports`.  Legacy aliases `"minecraft"` and `"ts3"` are still accepted and normalized.  Every maintained game module must define this wrapper in module scope, usually by calling shared builders through `import server.runtime as runtime_module`. |
| `get_container_spec` | `(server)` | Docker launch | Return the Docker launch spec: container working dir, command, stdin/tty settings, env, mounts, and published ports.  Keep this wrapper in module scope even when it delegates to shared runtime helpers. |

### Optional functions — add these where the server supports them

| Function | Signature | Backs command / purpose | Notes |
|---|---|---|---|
| `prestart` | `(server, *args, **kwargs)` | `start` (pre-hook) | Run immediately before the screen session is created — e.g. symlink Steam libraries, rotate logs. |
| `poststart` | `(server, *args, **kwargs)` | `start` (post-hook) | Run after the screen session starts — e.g. wait for a readiness marker, send init commands. |
| `sync_server_config` | `(server)` | `set` config sync | Rewrite on-disk game-server config files from datastore values that mirror real server config. Pair this with `config_sync_keys` so only valid game-config-backed keys trigger the sync. |
| `postset` | `(server, key, **kwargs)` | `set` (post-hook) | React to a data-store change — e.g. regenerate a config file when `port` is updated. |
| `get_query_address` | `(server)` | `query` | Return `(host, port, protocol)` so `Server.query()` uses the right address.  Protocol values: `"a2s"`, `"quake"`, `"ts3"`, `"tcp"`.  Without this hook the server falls back to `("127.0.0.1", data["port"], "a2s")`. |
| `get_info_address` | `(server)` | `info` | Return `(host, port, protocol)` so `Server.info()` uses the right address and protocol.  Protocol values: `"a2s"`, `"quake"`, `"slp"`, `"ts3"`, `"tcp"`.  Without this hook the server falls back to A2S then TCP.  **Always add this** unless the module uses `define_valve_server_module()` (which configures it automatically). |
| `update` | `(server, validate=False, restart=False, ...)` | `update` (extra command) | Update the server binary via SteamCMD or another mechanism.  Stop the server first, then optionally restart.  Add `"update"` to `commands` and entries in `command_args`, `command_descriptions`, and `command_functions`. |
| `restart` | `(server, ...)` | `restart` (extra command) | Custom restart logic.  The default `Server.restart()` simply calls `stop()` then `start()`, so only add this if the server needs different behaviour.  Add `"restart"` to `commands` etc. as above. |
| `wipe` | `(server)` | `wipe` | Delete world / save data.  Alternatively set `wipe_paths` (list of paths relative to the install dir) and the built-in handler iterates them. |

### Module-level attributes

| Attribute | Type | Required | Notes |
|---|---|---|---|
| `commands` | `tuple[str, ...]` | Yes | Extra command names beyond the built-in set (e.g. `("update", "restart")`).  Use `()` if none. |
| `command_args` | `dict[str, CmdSpec]` | Yes | Argument specs for every command in `commands` plus any built-in commands whose args the module extends. |
| `command_descriptions` | `dict[str, str]` | Yes | Human-readable description for every command in `commands`. |
| `command_functions` | `dict[str, callable]` | Yes | Implementation function for every command in `commands`. |
| `max_stop_wait` | `int` | No | Maximum minutes to wait for a graceful stop before the `Server` class kills the process.  Capped at 5 minutes.  Default is 5 if omitted. |
| `config_sync_keys` | `tuple[str, ...]` or iterable | Conditional | Required when any `set`-able datastore keys map directly to real game-server config values. List only the top-level keys that represent actual game-server config. Do not include AlphaGSM-only keys such as internal runtime metadata, backup settings, install-only fields, or other manager-only values. |

### Quick checklist for a new module

Before marking a new game module complete, verify all of these:

- [ ] `commands`, `command_args`, `command_descriptions`, `command_functions` are defined
- [ ] the canonical top-level module import surface is `<module>/__init__.py`
- [ ] the primary top-level module implementation lives in `<module>/main.py`
- [ ] if the module carries local curated manifests or multiple support files, those assets live beside the package-backed module implementation instead of as sibling top-level files
- [ ] `configure` stores at minimum `port` and `dir` in `server.data`
- [ ] `configure` initialises `server.data["backup"]` with a default profile and schedule
- [ ] `configure` returns `((), {})` (or args/kwargs to forward to `install`)
- [ ] `install` downloads or copies all files and calls `server.data.save()`
- [ ] `get_start_command` returns `(argv_list, working_dir)` with the correct executable path
- [ ] `do_stop` sends a graceful stop command through the runtime-aware helper (e.g. `runtime_module.send_to_server(server, "\nquit\n")`)
- [ ] `status` at minimum passes (no-op is acceptable if no extra info is available)
- [ ] `message` either sends a message through the active runtime input path or prints a clear "not supported" explanation
- [ ] `backup` calls `backup_utils.backup(...)` with the correct arguments
- [ ] `checkvalue` handles `"port"`, `"dir"`, `"exe_name"` (where stored), and `"backup"` keys
- [ ] `checkvalue` or shared validation covers any claim-affecting hosted-IP keys the module stores (`bindaddress`, `publicip`, `externalip`, `hostip`)
- [ ] if any `set`-able keys map to real game-server config, `sync_server_config(server)` exists and `config_sync_keys` lists exactly those top-level keys
- [ ] `config_sync_keys` excludes AlphaGSM-only keys such as backup config, runtime metadata, install-cache fields, or manager-only convenience values
- [ ] if the module exposes map-like `set` keys such as `map`, `startmap`, `world`, `level`, or `mission`, validate them against installed content, declared supported defaults, or another module-specific allowlist when practical
- [ ] `get_info_address` is defined and returns the correct `(host, port, protocol)` tuple
- [ ] `get_query_address` is defined if the query port differs from the game port or the server uses a non-A2S protocol
- [ ] `import server.runtime as runtime_module` appears in modules that use shared Docker builders
- [ ] `get_runtime_requirements` and `get_container_spec` are available in module scope and describe the correct image family, env, mounts, and ports through explicit wrappers
- [ ] runtime/container claim metadata can be derived during `setup` before `install` finishes; do not make `get_container_spec` depend on already-installed files unless the setup-time path has a safe fallback
- [ ] `update` and `restart` are wired up in `commands` / `command_functions` if offered
- [ ] at least one unit test exists under `tests/unit_tests/` for the module or its shared helper surface
- [ ] one integration test exists at `tests/integration_tests/test_<module>.py`
- [ ] the integration test exercises the AlphaGSM lifecycle, including `create`, `setup`, `start`, readiness, `status`, `query`, `info`, `info --json`, and `stop`
- [ ] Source-engine integration coverage either keeps the server awake or wires an explicit wake-on-query/info hook rather than accepting hibernation as "good enough"
- [ ] The module passes `make lint` with a score of `10.00/10`

## Curated Mod And Plugin Work

When a module exposes `mod add manifest ...` or another checked-in curated
registry flow, treat that registry as part of the module lifecycle contract.

- Prefer popular, high-value curated families backed by authoritative release assets.
- Declare dependencies in the checked-in registry instead of relying on docs or user ordering.
- Make the desired/apply path install declared dependencies automatically.
- Keep the registry beside the canonical module implementation when the module is package-backed.
- If a checked-in registry is intentionally shared across multiple game modules through one helper surface, keep it in the shared helper path instead of forcing it into an unrelated canonical module package.
- Expand shared helpers when upstream payloads reveal a real packaging gap, rather than hardcoding one-off install logic in a single module.
- Add unit coverage for checked-in manifest resolution and at least one apply/install path when the payload shape is new.

## Test Expectations For New Server Types

When adding a new game server, treat the lifecycle work as incomplete until it has appropriate test coverage across the repository's test layers:

- unit tests for command parsing, protocol hooks, config generation, or other module behaviour — run with `make test`
- integration tests for end-to-end pytest coverage through the `alphagsm` CLI — run with `make integration-test` (requires `ALPHAGSM_WORK_DIR`)
- smoke tests for a streamed real-world lifecycle example — run with `make smoke-test SMOKE_TEST=run_<name>.sh`

The smoke tests are not owned by this skill, but new server lifecycle work should still result in smoke coverage being added or updated.

## Integration Test Standards

Integration tests use helpers from `tests/integration_tests/conftest.py`.

### Minimum required coverage

Every new game module must land with **both**:

- at least one unit test under `tests/unit_tests/`
- one AlphaGSM-driven integration test under `tests/integration_tests/test_<module>.py`

Every integration test for a game server module **must** exercise all of these
steps, in order, without any of them being silently skipped:

1. **`create`** — create the server entry
2. **`setup`** — install/configure the server (SteamCMD download, config write, etc.)
3. **start + readiness** — start the server and wait for a log marker that
   confirms it is actually ready to accept connections
4. **`status`** — assert the server reports running
5. **`query`** — assert the server responds to network query
6. **`info`** — assert the server returns human-readable info
7. **`info --json`** — assert valid JSON with correct protocol field
8. **`stop`** — stop the server
9. **shutdown verification** — wait for the port to close

If a game server module genuinely does not implement one of these commands,
the module itself needs to be fixed to provide a meaningful result (e.g. TCP
ping fallback for query), not the test skipped.

### Port ownership rules

When you add or edit a module, keep the shared port-manager behaviour in mind:

- `set` rejects conflicting claim changes immediately. This includes primary
  and optional `*port` keys, hosted-IP keys, and runtime-published `ports`
  metadata if the module exposes it.
- `setup` is the only phase allowed to auto-shift ports, and it must shift the
  entire claimed port group together rather than one port at a time.
- Explicit user intent persists. Once a claim key is explicit, later `setup`
  runs must keep treating it as explicit until the user changes it again.
- `start` must fail before launch if any claimed port is already occupied by a
  managed AlphaGSM server or a live listener on the same hosted IP.
- Collision checks ignore protocol, so `27015/tcp` and `27015/udp` still
  conflict if they target the same hosted IP.

## Runtime Families

When adding container support, prefer these shared runtime families before
inventing a one-off image strategy:

- `java` for jar-based Java servers and proxies, including Minecraft-family modules
- `quake-linux` for native Linux Quake-family servers
- `service-console` for TeamSpeak 3 and similar console-driven TCP service daemons
- `simple-tcp` for lightweight daemon-style services that just need mounted config/data and published ports
- `steamcmd-linux` for Linux-native SteamCMD installs
- `wine-proton` only when there is no viable native path yet

If a module fits one of these families, wire it to that family first and only
then add game-specific environment or port details inside the explicit module
wrappers.

When reviewing or editing an existing module, preserve those Docker run details.
Do not treat container metadata as optional follow-up work.

Back-end Docker lifecycle coverage lives under
`tests/backend_integration_tests/docker_family_matrix.py`. Keep three declared
representative cases per runtime family. Any case marked active there must run
in CI through `tests/backend_integration_tests/test_backend_docker.py` and
prove the same AlphaGSM lifecycle contract as the regular integration suite.

For Windows-only modules that already use `utils.proton.wrap_command(...)`,
prefer the shared `utils.proton.get_runtime_requirements(...)` and
`utils.proton.get_container_spec(...)` helpers plus the container scaffold
under `docker/wine-proton/`, but keep the module wrappers explicit in source.

### The integration flow must use AlphaGSM commands

The integration test is a contract test for the public AlphaGSM workflow.
Do **not** start the server binary directly from pytest and then call that
"integration coverage". Use `run_and_assert_ok(...)` / `run_alphagsm(...)`
for the lifecycle commands.

At minimum, the integration test must prove this ordered AlphaGSM lifecycle:

1. `alphagsm <name> create <module>`
2. `alphagsm <name> setup ...`
3. `alphagsm <name> start`
4. readiness verification before network assertions
5. `alphagsm <name> query`
6. `alphagsm <name> info`
7. `alphagsm <name> stop`

In practice, new-module tests should use the full canonical sequence:
`create`, `setup`, `start`, readiness, `status`, `query`, `info`,
`info --json`, `stop`, shutdown verification.

### Hibernation is not a valid end state for new-module tests

For new game module coverage, "the server reached a hibernating idle state" is
**not** enough. The test must prove the server is awake enough that the real
query and info protocol succeeds.

- Do **not** treat `Server is hibernating` as the only success marker for a
  new Source-engine module.
- Do **not** accept TCP fallback as proof that a new A2S-based module is
  healthy.
- If a Source server hibernates by default, first prefer a supported
  integration-only config or startup adjustment that keeps it queryable during
  the test.
- If the current build ignores that config, add a module wake hook for
  `query` / `info` that sends a harmless console command such as `status`, lets
  the server answer A2S, and then allows the engine to re-enter hibernation
  naturally.
- Run the protocol-specific readiness helper before `query` / `info`, then
  assert the exact protocol in `info --json`.

### No soft skips — ever

**Rule**: a test must either pass or be explicitly disabled at the whole-test
level. Silent mid-test skips are forbidden.

- Do **not** write `pytest.skip(...)` inside a passing test body to paper over
  a command that does not work.
- Do **not** use `if result.returncode != 0: pytest.skip(...)` for any command.
- Do **not** guard `query` or `info` assertions with optional `if` branches
  (e.g. `if _info_data["protocol"] == "a2s": ...` to avoid checking when TCP
  falls back).
- There is no `run_soft_query` helper and there should never be one again.

The **only** acceptable skip is when the server cannot be installed or started
at all in the current environment (Windows-only binary, no credentials, dead
download URL). Those cases go through `skip_for_known_steamcmd_issue` inside
`run_and_assert_ok`, or via `pytest.mark.skip` on the whole test function.

### Timeouts are FAILURES, not skips

The wait helpers (`wait_for_log_marker`, `wait_for_a2s_ready`,
`wait_for_quake_ready`, `wait_for_tcp_open`) all call `pytest.fail()` on
timeout — **not** `pytest.skip()`. This is intentional.

A timeout means the server did not become ready within the allowed window.
That is a real problem requiring a real fix:

- **Wrong readiness marker** — update the marker string to match what the
  server actually prints.
- **Server crashes on startup** — fix the crash; read the `[diagnostic]` log
  tail printed before the failure.
- **Wrong query port** — ensure the test passes the port the server actually
  listens on for A2S / Quake / TCP queries.
- **Timeout genuinely too short** — raise the `timeout_seconds` argument in
  the test (e.g. for servers that take >5 minutes to load their world).
  Long timeouts (30–60 minutes) are acceptable in CI for servers that
  require large SteamCMD downloads, world generation, or slow UE4/Proton
  initialisation.  Add `@pytest.mark.timeout(3600)` and increase both
  `START_TIMEOUT` and `wait_for_a2s_ready()` `timeout_seconds` accordingly.
  Also add the test file to the `SLOW_TESTS` list in
  `.github/workflows/unittest.yaml` so CI schedules it as a solo batch rather
  than blocking other tests.

**Never** respond to a timeout failure by:
- Changing `pytest.fail()` back to `pytest.skip()`
- Adding the server to `disabled_servers.conf`
- Wrapping the wait call in a `try/except`

### Fix the issue, not the test

If an integration test fails, the correct response is:

1. Diagnose the root cause in the server module or AlphaGSM code.
2. Search the web for upstream dedicated-server docs, release notes, issue
   reports, and runtime/dependency guidance that might explain the failure.
   Prioritise official sources.
3. Fix the code, config, or environment so the server actually works.
4. Keep the test assertion strict.

Do **not** loosen assertions to make a broken server appear to pass.  
Do **not** add soft skips to hide failures.

Treat enablement as the default goal:

- A server is "enabled" only when its integration test passes.
- Prefer re-enabling a broken server over normalising its disabled state.
- Only move a module to `disabled_servers.conf` after you have exhausted
  realistic fixes, including upstream web research for required settings,
  assets, and host dependencies.

### Protocol certainty for `info --json`

Every server has exactly one network protocol that `info` should use.
The integration test must assert the **exact** protocol, not a union:

```python
# CORRECT — assert the one protocol this server uses
assert _info_data["protocol"] == "a2s", ...

# WRONG — "in" disguises uncertainty about what protocol was actually used
assert _info_data["protocol"] in ("a2s", "tcp"), ...
```

If the test fails because the wrong protocol was returned, the root cause is
almost always one of:

- The game module is missing a `get_info_address()` hook → add one returning
  `("127.0.0.1", server.data["port"], "<protocol>")` so `Server.info()` does
  not fall back to TCP.
- The wrong protocol string was used in the assertion → correct the assertion
  to match what the server actually speaks.

Never widen the assertion to include both the correct protocol and the TCP
fallback.

Known protocol strings used by `info --json`:
- `"a2s"` — Valve A2S_INFO (Source / GoldSrc engines)
- `"quake"` — Quake-family `getstatus` / `status` query
- `"slp"` — Minecraft Server List Ping
- `"ts3"` — TeamSpeak 3 ServerQuery
- `"tcp"` — raw TCP ping (last-resort fallback; should not appear if the
  module has a proper `get_info_address()` hook)

### Canonical integration test pattern

Use this pattern for modules with a rich query/info protocol such as A2S,
Quake, or SLP. For genuinely TCP-only modules, adapt the expected output text
to the TCP-specific response — but do not weaken rich-protocol modules down to
TCP fallback assertions.

```python
# start
run_and_assert_ok(env, server_name, "start")

# readiness
wait_for_log_marker(log_path, [...], START_TIMEOUT)
wait_for_a2s_ready("127.0.0.1", port, 120, log_path=log_path)  # or quake/tcp helper

# query
query_result = run_and_assert_ok(env, server_name, "query")
assert (
    "Server is responding" in query_result.stdout
), f"Unexpected query output: {query_result.stdout!r}"

# info
info_result = run_and_assert_ok(env, server_name, "info")
assert "Players" in info_result.stdout, (
    f"Unexpected info output: {info_result.stdout!r}"
)

# info --json
import json as _info_json
info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
_info_data = _info_json.loads(info_json_result.stdout.strip())
assert _info_data["protocol"] == "a2s", (   # replace with the actual protocol
    f"Expected a2s protocol in info JSON: {_info_data!r}"
)
assert _info_data.get("players") == 0, (
    f"Expected 0 players on fresh server: {_info_data!r}"
)

# stop
run_and_assert_ok(env, server_name, "stop")
```

## Running Integration Tests On Low Disk Space

SteamCMD game servers can be very large (1–15 GB each). When disk space is limited:

- Use `make integration-test` — it runs one test at a time and cleans up between each automatically.
- To run a single test: `make integration-test IT_TEST=tests/integration_tests/test_<name>.py`
- Both require `ALPHAGSM_WORK_DIR` to be set to a directory with enough free space (~50 GB):
  ```bash
  export ALPHAGSM_WORK_DIR=/mnt/data/gsm-work
  make integration-test
  ```
- After each test finishes, **delete the pytest temp directory** to reclaim space:
  ```bash
  rm -rf /tmp/pytest-of-$(whoami)/pytest-current/
  ```
  (`make integration-test` does this automatically via `run_integration_tests.sh`.)
- Check free space before each test with `df -h /`.
- If a test installs a large game and fails, clean up before retrying.
- Consider keeping a SteamCMD download cache (`~/Steam/steamapps/`) across runs to avoid re-downloading unchanged files — but delete per-server install dirs from the work dir.

## Files To Inspect

- `server/server.py`
- `core/main.py`
- `screen/screen.py`

## Integration Test Status Tracking

The file `docs/TEST_STATUS.md` tracks every integration test and its
current state: **PASSED**, **DISABLED**, **SKIPPED**, or **RUNNABLE**.

### Agent requirement

Every time an agent runs integration tests it **must** update `TEST_STATUS.md`
**immediately after each test** — not in a batch at the end:

1. **After a test passes** — move it from RUNNABLE to PASSED with the correct
   type (SteamCMD, Source, GoldSrc, Direct download, Archive, etc.)
   **right away, before running the next test**.
2. **After disabling a server** — move it from RUNNABLE to DISABLED and record
   the reason (must also match `disabled_servers.conf`). Do this **immediately**.
3. **After adding a skip marker** — move it from RUNNABLE to SKIPPED with the
   reason. Do this **immediately**.
4. **Update the summary counts** at the top of the file after every change.
5. **Update the "Last updated" date** after every change.

**Bulk runs**: When running many tests in sequence, update `TEST_STATUS.md`
after **every single test**, not at the end. This ensures progress is never
lost if a session is interrupted.

### How to regenerate the list from scratch

```bash
cd /home/cosmosquark/sector_alpha/github/AlphaGSM
# Build disabled list
cut -f1 disabled_servers.conf | grep -v '^#' | grep -v '^$' | sort > /tmp/disabled.txt
# Build passed list (update with known-passed test names)
sort /tmp/passed.txt -o /tmp/passed.txt
# Classify
for f in tests/integration_tests/test_*.py; do
  t=$(echo "$f" | sed 's|.*/test_||;s|\.py||')
  if grep -qFx "$t" /tmp/disabled.txt; then echo "DISABLED  $t"
  elif grep -qFx "$t" /tmp/passed.txt; then echo "PASSED    $t"
  elif grep -q 'pytest.mark.skip' "$f"; then echo "SKIPPED   $t"
  else echo "RUNNABLE  $t"
  fi
done | sort -k1,1
```

### Cross-references

- `disabled_servers.conf` — authoritative list of disabled modules and reasons.
- `docs/TEST_STATUS.md` — human-readable tracker.
- Both files must stay in sync.
- `tests/smoke_tests/*.sh`
- the relevant `gamemodules/...` file

## Server Disabling Process

When integration tests fail and a server needs to be disabled, follow this exact sequence:

### 1. Add to disabled_servers.conf

**Format**: `module_name<TAB>reason`

**Common failure reasons**:
- `SteamCMD app XXXXXX is Windows-only (ExecutableName.exe)`
- `SteamCMD app XXXXXX requires authentication (No subscription)`
- `SteamCMD app XXXXXX installs no Linux-compatible dedicated server binary (executable file not found)`
- `SteamCMD downloads successfully but server never outputs expected readiness markers`
- `Download domain example.com is dead`
- `Server starts but crashes during initialization before log markers appear (crash pattern)`
- `Can't start server that is already running (process management issue during setup)`

### 2. Update TEST_STATUS.md

Move the server from RUNNABLE to DISABLED section with the **same reason** as disabled_servers.conf:

```markdown
| servername | Reason from disabled_servers.conf |
```

Update summary counts at the top.

### 3. Disable corresponding smoke test

**Location**: `tests/smoke_tests/run_[servername].sh`

**Method**: Add early exit with informative message:

```bash
#!/usr/bin/env bash
# DISABLED: This smoke test is disabled because the server failed, is disabled, or was skipped in integration testing
# See docs/TEST_STATUS.md for current server status
echo "Smoke test for [servername] is disabled - see docs/TEST_STATUS.md for status"
exit 0

# Original test code follows (preserved but unreachable)...
```

### 4. Verification

Ensure all three files stay synchronized:
- `disabled_servers.conf` entry exists
- `docs/TEST_STATUS.md` DISABLED section updated
- `tests/smoke_tests/run_[servername].sh` disabled with early exit

**Never disable servers without proper documentation** — every disabled server must have a clear, actionable reason that explains why it cannot run on the target platform.

## Update Rule

If lifecycle behaviour changes, update all relevant:

- integration tests
- smoke tests
- server guide docs
- `README.md`
- `DEVELOPERS.md`

If a new game server is added, verify that it participates in the standard command contract before treating it as complete.

If a new game server requires a user-supplied `--url` rather than a built-in resolver, also:

- document the expected archive type and executable
- add or update an entry in `docs/manual-download-fallbacks.md`
- prefer an official or project-maintained release source when one exists
- add a built-in resolver instead of a manual `--url` flow whenever there is a stable official API or predictable release pattern
