# Ricochet

This guide covers the `ricochetserver` module in AlphaGSM.

`ricochetserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myricochet create ricochetserver
```

Run setup:

```bash
alphagsm myricochet setup
```

Start it:

```bash
alphagsm myricochet start
```

Check it:

```bash
alphagsm myricochet status
```

Stop it:

```bash
alphagsm myricochet stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myricochet update
alphagsm myricochet backup
```

## Notes

- Module name: `ricochetserver`
- Default port: 27015
- Process and Docker integration readiness use AlphaGSM `info --json` protocol
  `a2s`; Docker does not require a host `screen` log.

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `ricochet`
- **Launcher resolution**: the shared GoldSrc launcher prefers `hlds_run`
  before falling back to lower-level binaries

### Server Configuration

- **Config file**: `ricochet/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `rc_arena`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/ricochetserver/](../server-templates/ricochetserver/)

### Maps and Mods

- **Map directory**: `ricochet/maps/`
- **Mod directory**: `ricochet/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `ricochet/maps/` and add to `ricochet/mapcycle.txt`.
- **Mod install**: Use Metamod in `ricochet/dlls/` or AMX Mod X in `ricochet/addons/amxmodx/`.
