# Natural Selection

This guide covers the `nsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynsserver create nsserver
```

Run setup:

```bash
alphagsm mynsserver setup
```

`nsserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the base
HLDS runtime through SteamCMD, but Steam app `90` does not provide the Natural
Selection mod payload. Before `start`, copy a complete owned Natural Selection
content tree into `<install_dir>/ns/` so
`<install_dir>/ns/maps/ns_hera.bsp` exists.

Start it:

```bash
alphagsm mynsserver start
```

Check it:

```bash
alphagsm mynsserver status
```

Stop it:

```bash
alphagsm mynsserver stop
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
alphagsm mynsserver create nsserver
alphagsm mynsserver setup -n 27015 /path/to/nsserver
# copy the full Natural Selection mod tree into /path/to/nsserver/ns/
alphagsm mynsserver start
```

## Useful Commands

```bash
alphagsm mynsserver update
alphagsm mynsserver backup
```

## Notes

- Module name: `nsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `ns/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `ns_hera`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/nsserver/](../server-templates/nsserver/)

### Maps and Mods

- **Map directory**: `ns/maps/`
- **Mod directory**: `ns/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `ns/maps/` and add to `ns/mapcycle.txt`.
- **Mod install**: Use Metamod in `ns/dlls/` or AMX Mod X in `ns/addons/amxmodx/`.
