# Counter-Strike

This guide covers the `csserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycsserver create csserver
```

Run setup:

```bash
alphagsm mycsserver setup
```

Start it:

```bash
alphagsm mycsserver start
```

Check it:

```bash
alphagsm mycsserver status
```

Stop it:

```bash
alphagsm mycsserver stop
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
alphagsm mycsserver update
alphagsm mycsserver backup
```

## Notes

- Module name: `csserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `cstrike/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `de_dust2`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/csserver/](../server-templates/csserver/)

### Maps and Mods

- **Map directory**: `cstrike/maps/`
- **Mod directory**: `cstrike/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `cstrike/maps/` and add to `cstrike/mapcycle.txt`.
- **Mod install**: Use Metamod in `cstrike/dlls/` or AMX Mod X in `cstrike/addons/amxmodx/`.
