# Half-Life: Deathmatch

This guide covers the `hldmserver` module in AlphaGSM.

`hldmserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhldmserv create hldmserver
```

Run setup:

```bash
alphagsm myhldmserv setup
```

Start it:

```bash
alphagsm myhldmserv start
```

Check it:

```bash
alphagsm myhldmserv status
```

Stop it:

```bash
alphagsm myhldmserv stop
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
alphagsm myhldmserv update
alphagsm myhldmserv backup
```

## Notes

- Module name: `hldmserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create hldmserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `crossfire`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Half-Life: Deathmatch`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`

### Server Configuration

- **Config file**: `valve/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `crossfire`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/hldmserver/](../server-templates/hldmserver/)

### Maps and Mods

- **Map directory**: `valve/maps/`
- **Mod directory**: `valve/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `valve/maps/` and add to `valve/mapcycle.txt`.
- **Mod install**: Use Metamod in `valve/dlls/` or AMX Mod X in `valve/addons/amxmodx/`.
