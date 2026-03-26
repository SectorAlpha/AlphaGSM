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
