# The Specialists

This guide covers the `tsserver` module in AlphaGSM.

`tsserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that owned-mod-content prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytsserver create tsserver
```

Run setup:

```bash
alphagsm mytsserver setup
```

`tsserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the base
HLDS runtime through SteamCMD, but Steam app `90` does not provide The
Specialists mod payload. Before `start`, copy a complete owned The Specialists
content tree into `<install_dir>/ts/` so
`<install_dir>/ts/maps/ts_neobaroque.bsp` exists.

Start it:

```bash
alphagsm mytsserver start
```

Check it:

```bash
alphagsm mytsserver status
```

Stop it:

```bash
alphagsm mytsserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Suggested flow:

```bash
alphagsm mytsserver create tsserver
alphagsm mytsserver setup -n 27015 /path/to/tsserver
# copy the full The Specialists mod tree into /path/to/tsserver/ts/
alphagsm mytsserver start
```

## Useful Commands

```bash
alphagsm mytsserver update
alphagsm mytsserver backup
```

## Notes

- Module name: `tsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `ts/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `ts_neobaroque`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/tsserver/](../server-templates/tsserver/)

### Maps and Mods

- **Map directory**: `ts/maps/`
- **Mod directory**: `ts/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `ts/maps/` and add to `ts/mapcycle.txt`.
- **Mod install**: Use Metamod in `ts/dlls/` or AMX Mod X in `ts/addons/amxmodx/`.
