# Day of Defeat

This guide covers the `dodserver` module in AlphaGSM.

`dodserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydodserve create dodserver
```

Run setup:

```bash
alphagsm mydodserve setup
```

Start it:

```bash
alphagsm mydodserve start
```

Check it:

```bash
alphagsm mydodserve status
```

Stop it:

```bash
alphagsm mydodserve stop
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
alphagsm mydodserve update
alphagsm mydodserve backup
```

## Notes

- Module name: `dodserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create dodserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `dod_Anzio`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Day of Defeat`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `dod`

### Server Configuration

- **Config file**: `dod/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dod_Anzio`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/dodserver/](../server-templates/dodserver/)

### Maps and Mods

- **Map directory**: `dod/maps/`
- **Mod directory**: `dod/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dod/maps/` and add to `dod/mapcycle.txt`.
- **Mod install**: Use Metamod in `dod/dlls/` or AMX Mod X in `dod/addons/amxmodx/`.
