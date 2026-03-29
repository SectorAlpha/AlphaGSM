# Server Lifecycle

| Field | Value |
| --- | --- |
| Purpose | Preserve, document, and enforce the standard AlphaGSM server lifecycle contract. |
| Use when | Changing lifecycle code, adding a new game server, or documenting per-server behaviour. |
| Main source | `server/server.py`, `core/main.py`, smoke tests, and the relevant game module. |

| Field | Value |
| --- | --- |
| Inputs | Server dispatch logic, default command contract, and game module lifecycle code. |
| Outputs | Updated lifecycle code, matching docs, matching tests, and command-contract compliance for new modules. |
| Related files | `server/server.py`, `core/main.py`, `screen/screen.py`, `gamemodules/**`, `tests/server/*`, `tests/smoke_tests/*.sh`. |

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

Where applicable, it should also integrate cleanly with:

- `message`
- `backup`
- `connect`
- `dump`
- `set`

The goal is that a user can create and operate a new server type using the same AlphaGSM mental model they already use for Minecraft, TF2, or CS:GO.

## Test Expectations For New Server Types

When adding a new game server, treat the lifecycle work as incomplete until it has appropriate test coverage across the repository's test layers:

- unit tests for command parsing and module behaviour — run with `make test`
- integration tests for end-to-end pytest coverage — run with `make integration-test` (requires `ALPHAGSM_WORK_DIR`)
- smoke tests for a streamed real-world lifecycle example — run with `make smoke-test SMOKE_TEST=run_<name>.sh`

The smoke tests are not owned by this skill, but new server lifecycle work should still result in smoke coverage being added or updated.

## Integration Test Standards

Integration tests use helpers from `tests/integration_tests/conftest.py`.

### Minimum required coverage

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

### Fix the issue, not the test

If an integration test fails, the correct response is:

1. Diagnose the root cause in the server module or AlphaGSM code.
2. Fix the code so the server actually works.
3. Keep the test assertion strict.

Do **not** loosen assertions to make a broken server appear to pass.  
Do **not** add soft skips to hide failures.

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
- `"slp"` — Minecraft Server List Ping
- `"tcp"` — raw TCP ping (last-resort fallback; should not appear if the
  module has a proper `get_info_address()` hook)

### Canonical integration test pattern

```python
# query
query_result = run_and_assert_ok(env, server_name, "query")
assert (
    "Server is responding" in query_result.stdout
    or "Server port is open" in query_result.stdout
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
