# Sven Co-op

This guide covers the `svenserver` module in AlphaGSM.

`svenserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysvenserv create svenserver
```

Run setup:

```bash
alphagsm mysvenserv setup
```

Start it:

```bash
alphagsm mysvenserv start
```

Check it:

```bash
alphagsm mysvenserv status
```

Stop it:

```bash
alphagsm mysvenserv stop
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
alphagsm mysvenserv update
alphagsm mysvenserv backup
```

## Notes

- Module name: `svenserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create svenserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `svencoop1`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Sven Co-op`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `svends_run`
- **Location**: `<install_dir>/svends_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `276060`

### Server Configuration

- **Config file**: `svencoop/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `svencoop1`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/svenserver/](../server-templates/svenserver/)

### Maps and Mods

- **Map directory**: `svencoop/maps/`
- **Mod directory**: `svencoop/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `svencoop/maps/` and add to `svencoop/mapcycle.txt`.
- **Mod install**: Use Metamod in `svencoop/dlls/` or AMX Mod X in `svencoop/addons/amxmodx/`.
