# Left 4 Dead

This guide covers the `l4dserver` module in AlphaGSM.

`l4dserver` is currently `PASSED` in the checked-in support tracker on the
documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane
validates both process and Docker runtimes for this module, while local runs
remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myl4dserve create l4dserver
```

Run setup:

```bash
alphagsm myl4dserve setup
```

Start it:

```bash
alphagsm myl4dserve start
```

Check it:

```bash
alphagsm myl4dserve status
```

Stop it:

```bash
alphagsm myl4dserve stop
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
alphagsm myl4dserve update
alphagsm myl4dserve backup
```

## Notes

- Module name: `l4dserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create l4dserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `l4d_hospital01_apartment`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `8`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Left 4 Dead`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `222840`

### Server Configuration

- **Config file**: `left4dead/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `l4d_hospital01_apartment`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/l4dserver/](../server-templates/l4dserver/)

### Maps and Mods

- **Map directory**: `left4dead/maps/`
- **Mod directory**: `left4dead/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/left4dead/`.
- **Map install**: Copy `.bsp` files into `left4dead/maps/` and add to `left4dead/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `left4dead/addons/`.
