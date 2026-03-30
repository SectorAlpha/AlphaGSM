# Server Info Gathering

| Field | Value |
| --- | --- |
| Purpose | Extract, document, and maintain per-server developer notes covering run files, properties, and mod/map installation. |
| Use when | Adding developer notes to server docs, onboarding a new game module, or auditing existing server configurations. |
| Main source | Game module source in `src/gamemodules/`, installed server directories, and `src/utils/valve_server.py`. |

| Field | Value |
| --- | --- |
| Inputs | Game module Python source, SteamCMD app metadata, installed server file trees. |
| Outputs | Developer notes sections in `docs/servers/*.md`, config templates in `docs/server-templates/`. |
| Related files | `src/gamemodules/**`, `src/utils/valve_server.py`, `docs/servers/*.md`, `docs/server-templates/`. |

Use this skill when populating or updating the Developer Notes section of a server guide.

## What To Gather

For every game module, collect three categories of information:

### 1. Run File Location

Where the server executable lives relative to the install directory.

Sources:

- `get_start_command()` in the game module — returns `(command_list, working_dir)`
- For Valve servers: `define_valve_server_module(executable=...)` in the module, plus the candidate search in `valve_server.py` `get_start_command()` which checks `srcds_run_64`, `srcds_run`, `srcds_run.sh`, `hlds_run`
- For non-Valve servers: the `exe_name` stored in `server.data["exe_name"]`

Record: the executable name, its path relative to install dir, and any runtime flags.

### 2. Server Properties / Config

Where the server reads its configuration and what the key settings are.

Sources:

- `configure()` in the game module — look for `server.data.setdefault("configfile", ...)` or hardcoded paths
- For Valve servers: `config_subdir` and `config_default` from `define_valve_server_module()`
- For Minecraft: `server.properties` in the install dir
- For other games: search for `.cfg`, `.ini`, `.yaml`, `.json`, `.toml`, `.xml` references in the module

Record: config file path relative to install dir, key settings (port, max players, map, RCON), and provide a config template.

### 3. Maps and Mods

How to install custom maps and mods for the server.

Sources:

- For Valve Source servers: maps go in `<game_dir>/maps/`, mods typically in `<game_dir>/addons/`
- For Valve GoldSrc (HLDS) servers: maps go in `<game_dir>/maps/`, mods in `<game_dir>/dlls/` or via Metamod
- For Minecraft: plugins go in `plugins/`, mods in `mods/`, maps in `world/`
- For other games: check the module for references to workshop, mod directories, or custom content paths
- SteamCMD Workshop: if the module sets `host_workshop_collection`, note that

Record: map directory, mod/plugin directory, workshop support (yes/no), and any special install steps.

## How To Extract Info Programmatically

### Valve Servers (Source and GoldSrc)

All Valve servers go through `define_valve_server_module()`. The parameters directly give:

```
executable      → run file name
game_dir        → base directory for game content
config_subdir   → config subdirectory (usually "cfg")
config_default  → main config file (usually "server.cfg")
default_map     → starting map
max_players     → player limit
port            → default game port
client_port     → client connection port
sourcetv_port   → SourceTV port (if applicable)
steam_app_id    → SteamCMD app ID
app_id_mod      → additional mod app ID (if applicable)
engine          → "source" or "goldsrc"
```

Maps: `<game_dir>/maps/`
Mods: `<game_dir>/addons/` (Source) or `<game_dir>/dlls/` (GoldSrc via Metamod)
Config: `<game_dir>/<config_subdir>/<config_default>`

### Non-Valve SteamCMD Servers

Read `configure()` and `get_start_command()` from the game module. Look for:

- `server.data["exe_name"]` — executable name
- `server.data["configfile"]` — config file path
- `server.data["dir"]` — install directory
- `steamcmd.download(...)` calls — SteamCMD app ID
- `server.data["port"]` — default port

### Non-SteamCMD Servers

Read `configure()`, `install()`, and `get_start_command()`. Look for:

- Download URLs and archive handling
- Custom install logic
- Config file creation or templating

## Template Format

Store config templates in `docs/server-templates/<module_name>/`:

- `server.cfg` or equivalent — the main config file with documented defaults
- `README.md` — brief notes on what each setting does

## Developer Notes Section Format

Add this section to each `docs/servers/<module>.md`:

```markdown
## Developer Notes

### Run File

- **Executable**: `<exe_name>`
- **Location**: `<install_dir>/<exe_name>`
- **Engine**: Source / GoldSrc / Custom
- **SteamCMD App ID**: <app_id>

### Server Configuration

- **Config file**: `<game_dir>/<config_subdir>/<config_default>`
- **Key settings**:
  - `port` — Game port (default: <port>)
  - `maxplayers` — Maximum players (default: <max>)
  - `map` — Starting map (default: <map>)
- **Template**: See `docs/server-templates/<module>/`

### Maps and Mods

- **Map directory**: `<game_dir>/maps/`
- **Mod directory**: `<game_dir>/addons/`
- **Workshop support**: Yes / No
- **Install steps**: Copy `.bsp` files into the map directory and add to `mapcycle.txt`
```

## Automation Plan

1. Parse each game module to extract parameters
2. Generate the Developer Notes section
3. Create config templates from defaults
4. Add the section to existing docs
5. Verify with lint and unit tests

## Integration Test Requirements for `info`

Every integration test must verify `info` and `info --json` with strict,
protocol-specific assertions. This section is the authoritative reference for
how to determine and assert the correct protocol.

### How to determine a server's info protocol

Look at the game module for a `get_info_address()` function:

```python
# If present, this determines the protocol used by Server.info()
def get_info_address(server):
    return ("127.0.0.1", server.data["port"], "<protocol>")
```

If `get_info_address()` is **absent**, `Server.info()` tries A2S first and
falls back to TCP. This fallback means the test cannot assert a stable protocol —
the right fix is to **add `get_info_address()`** to the module, not to
use `in ("a2s", "tcp")` in the test.

### Protocol reference

| Protocol string | When used |
|---|---|
| `"a2s"` | Valve A2S_INFO — Source and GoldSrc engines |
| `"slp"` | Minecraft Server List Ping — Vanilla, Spigot, Paper, BungeeCord, Waterfall, Velocity |
| `"tcp"` | Raw TCP ping — last-resort fallback only; should never appear if the module has `get_info_address()` |

### Adding `get_info_address()` to a module

For Source/GoldSrc servers the `define_valve_server_module()` call already
configures A2S automatically — do not add `get_info_address()` for those.

For all other modules that speak a known protocol, add:

```python
def get_info_address(server):
    """Return the address tuple for the ``info`` command."""
    return ("127.0.0.1", server.data["port"], "slp")  # or "a2s"
```

### Strict protocol assertion in integration tests

```python
# info --json — assert the EXACT protocol, never a union
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

If the test fails because `"tcp"` was returned instead of the expected protocol:

1. Check whether the module has `get_info_address()` — add it if missing.
2. Check whether the server is actually listening on the expected port by the
   time the test reaches `info`.
3. Do **not** change the assertion to `in ("a2s", "tcp")`.

## Query Protocol Capabilities & Full Property Verification

This section is the authoritative reference for what each query protocol
returns, what properties to assert, and how to ensure the server is ready for
querying before running assertions.

### Timing: wait before asserting

Log-file readiness markers (`wait_for_log_marker`) guarantee the server process
has started, but **not** that the UDP query port is accepting packets.  Use the
`wait_for_a2s_ready` helper (in `tests/integration_tests/conftest.py`) after
the log-marker check for any A2S server:

```python
wait_for_a2s_ready("127.0.0.1", port, 120)  # polls every 2 s, skips on timeout
```

If `wait_for_a2s_ready` times out, the test is marked as **skipped** (not
failed), because the server is not at fault.  This is the preferred behaviour:
we either prove A2S works, or we transparently admit we couldn't.

### Protocol: `"a2s"` — Valve A2S_INFO

Used by: Source engine (TF2, Gmod, CS:S, DOI, PVKII, ND, CC, …), GoldSrc,
and any game based on the Steam query protocol.

Implemented in: `src/utils/query.py` — `a2s_info()` + `parse_a2s_info()`

**Properties returned** (all present when parsing succeeds):

| Key | Type | Meaning |
|---|---|---|
| `name` | str | Server display name |
| `map` | str | Current map |
| `folder` | str | Game folder (e.g. `tf`, `garrysmod`) |
| `game` | str | Game description (e.g. `Team Fortress`) |
| `appid` | int | Steam Application ID |
| `players` | int | Current human player count |
| `max_players` | int | Maximum server capacity |
| `bots` | int | Bot player count |

**Full integration-test assertion template:**

```python
wait_for_a2s_ready("127.0.0.1", port, 120)

info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
_info_data = _info_json.loads(info_json_result.stdout.strip())
assert _info_data["protocol"] == "a2s", f"Expected a2s: {_info_data!r}"
assert _info_data["players"] == 0, f"Expected 0 players: {_info_data!r}"
assert _info_data["bots"] == 0, f"Expected 0 bots: {_info_data!r}"
assert isinstance(_info_data["name"], str) and _info_data["name"], f"name: {_info_data!r}"
assert isinstance(_info_data["map"], str), f"map: {_info_data!r}"
assert isinstance(_info_data["folder"], str) and _info_data["folder"], f"folder: {_info_data!r}"
assert isinstance(_info_data["game"], str), f"game: {_info_data!r}"
assert isinstance(_info_data["appid"], int) and _info_data["appid"] > 0, f"appid: {_info_data!r}"
assert _info_data["max_players"] > 0, f"max_players: {_info_data!r}"
```

### Protocol: `"quake"` — Quake3/QFusion getstatus

Used by: Warfork, Warsow, ET:Legacy, OpenArena, and Quake3-based servers.

Implemented in: `src/utils/query.py` — `quake_status()`

**Properties returned:**

| Key | Type | Meaning |
|---|---|---|
| `name` | str | Server display name (`sv_hostname` cvar) |
| `map` | str | Current map (`mapname` cvar) |
| `players` | int | Current player count (counted from player lines) |
| `max_players` | int | Maximum players (`sv_maxclients` cvar) |

**Full integration-test assertion template:**

```python
info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
_info_data = _info_json.loads(info_json_result.stdout.strip())
assert _info_data["protocol"] == "quake", f"Expected quake: {_info_data!r}"
assert _info_data["players"] == 0, f"Expected 0 players: {_info_data!r}"
assert isinstance(_info_data["name"], str), f"name: {_info_data!r}"
assert isinstance(_info_data["map"], str), f"map: {_info_data!r}"
assert _info_data["max_players"] > 0, f"max_players: {_info_data!r}"
```

### Protocol: `"slp"` — Minecraft Server List Ping

Used by: all Minecraft server variants (Vanilla, Spigot, Paper, BungeeCord,
Waterfall, Velocity).

Implemented in: `src/utils/query.py` — `slp_info()`

**Properties returned:**

| Key | Type | Meaning |
|---|---|---|
| `description` | str | Server MOTD / description |
| `players_online` | int | Current player count |
| `players_max` | int | Maximum player capacity |
| `version` | str | Server software version string |
| `player_names` | list[str] | Names of online players (only present when players are online) |

**Full integration-test assertion template:**

```python
info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
_info_data = _info_json.loads(info_json_result.stdout.strip())
assert _info_data["protocol"] == "slp", f"Expected slp: {_info_data!r}"
assert isinstance(_info_data["description"], str), f"description: {_info_data!r}"
assert _info_data["players_online"] == 0, f"Expected 0 players: {_info_data!r}"
assert _info_data["players_max"] > 0, f"players_max: {_info_data!r}"
assert isinstance(_info_data["version"], str) and _info_data["version"], f"version: {_info_data!r}"
```

### Protocol: `"ts3"` — TeamSpeak 3 ServerQuery

Used by: `ts3server` only.

Implemented in: `src/utils/query.py` — `ts3_serverinfo()` — opens a raw TCP
session to the TS3 ServerQuery port (default 10011), sends `serverinfo` and
`channellist` commands, and parses the escape-encoded responses.

**Properties returned:**

| Key | Type | Meaning |
|---|---|---|
| `name` | str | Virtual server name |
| `clients_online` | int | Connected client count |
| `max_clients` | int | Maximum client capacity |
| `uptime` | int | Server uptime in seconds |
| `platform` | str | Host OS platform string |
| `version` | str | TS3 server software version |
| `channels` | list[dict] | List of channel dicts: `{"id": int, "name": str}` |

TS3 always creates a **Default Channel** at first startup, so `channels` will
never be empty on a freshly started server.

**Full integration-test assertion template:**

```python
info_json_result = run_and_assert_ok(env, server_name, "info", "--json")
_info_data = _info_json.loads(info_json_result.stdout.strip())
assert _info_data["protocol"] == "ts3", f"Expected ts3: {_info_data!r}"
assert isinstance(_info_data["name"], str) and _info_data["name"], f"name: {_info_data!r}"
assert _info_data["clients_online"] == 0, f"clients_online: {_info_data!r}"
assert _info_data["max_clients"] > 0, f"max_clients: {_info_data!r}"
assert isinstance(_info_data["uptime"], int), f"uptime: {_info_data!r}"
assert isinstance(_info_data["platform"], str) and _info_data["platform"], f"platform: {_info_data!r}"
assert isinstance(_info_data["version"], str) and _info_data["version"], f"version: {_info_data!r}"
assert isinstance(_info_data["channels"], list) and len(_info_data["channels"]) > 0, (
    f"Expected non-empty channels list: {_info_data!r}"
)
assert all(isinstance(ch.get("name"), str) for ch in _info_data["channels"]), (
    f"All channels must have name strings: {_info_data!r}"
)
```

### Protocol: `"tcp"` — Raw TCP ping (fallback only)

`"tcp"` only returns `latency_ms` (float).  It carries **no real server
information**.  A test that asserts `protocol == "tcp"` is not proving the
server works — it is proving the port is open.

Rule: **never accept `"tcp"` as a valid result for servers that have a richer
protocol available.**  If a module falls back to TCP, add `get_info_address()`
(or `get_query_address()`) to the game module to return the correct protocol.


