# BrainBread

This guide covers the `bbserver` module in AlphaGSM.

`bbserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
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
alphagsm mybbserver create bbserver
```

Run setup:

```bash
alphagsm mybbserver setup
```

`bbserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the base
HLDS runtime through SteamCMD, but Steam app `90` does not provide the
BrainBread mod payload. Before `start`, copy a complete owned BrainBread
content tree into `<install_dir>/brainbread/` so
`<install_dir>/brainbread/maps/bb_chp4_slaywatch.bsp` exists.

Start it:

```bash
alphagsm mybbserver start
```

Check it:

```bash
alphagsm mybbserver status
```

Stop it:

```bash
alphagsm mybbserver stop
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
alphagsm mybbserver create bbserver
alphagsm mybbserver setup -n 27015 /path/to/bbserver
# copy the full BrainBread mod tree into /path/to/bbserver/brainbread/
alphagsm mybbserver start
```

## Useful Commands

```bash
alphagsm mybbserver update
alphagsm mybbserver backup
```

## Notes

- Module name: `bbserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create bbserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `bb_chp4_slaywatch`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM BrainBread`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `brainbread/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `bb_chp4_slaywatch`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/bbserver/](../server-templates/bbserver/)

### Maps and Mods

- **Map directory**: `brainbread/maps/`
- **Mod directory**: `brainbread/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `brainbread/maps/` and add to `brainbread/mapcycle.txt`.
- **Mod install**: Use Metamod in `brainbread/dlls/` or AMX Mod X in `brainbread/addons/amxmodx/`.
