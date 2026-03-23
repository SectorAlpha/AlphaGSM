# Vampire Slayer

This guide covers the `vsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvsserver create vsserver
```

Run setup:

```bash
alphagsm myvsserver setup
```

Start it:

```bash
alphagsm myvsserver start
```

Check it:

```bash
alphagsm myvsserver status
```

Stop it:

```bash
alphagsm myvsserver stop
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
alphagsm myvsserver update
alphagsm myvsserver backup
```

## Notes

- Module name: `vsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `vs/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `vs_frost`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/vsserver/](../server-templates/vsserver/)

### Maps and Mods

- **Map directory**: `vs/maps/`
- **Mod directory**: `vs/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `vs/maps/` and add to `vs/mapcycle.txt`.
- **Mod install**: Use Metamod in `vs/dlls/` or AMX Mod X in `vs/addons/amxmodx/`.
