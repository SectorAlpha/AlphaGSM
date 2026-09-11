# No More Room in Hell

This guide covers the `nmrihserver` module in AlphaGSM.

`nmrihserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynmrihser create nmrihserver
```

Run setup:

```bash
alphagsm mynmrihser setup
```

Start it:

```bash
alphagsm mynmrihser start
```

Check it:

```bash
alphagsm mynmrihser status
```

Stop it:

```bash
alphagsm mynmrihser stop
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
alphagsm mynmrihser update
alphagsm mynmrihser backup
```

## Notes

- Module name: `nmrihserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create nmrihserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `nmo_broadway`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `8`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM No More Room in Hell`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `317670`

### Server Configuration

- **Config file**: `nmrih/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `nmo_broadway`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/nmrihserver/](../server-templates/nmrihserver/)

### Maps and Mods

- **Map directory**: `nmrih/maps/`
- **Mod directory**: `nmrih/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/nmrih/`.
- **Map install**: Copy `.bsp` files into `nmrih/maps/` and add to `nmrih/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nmrih/addons/`.
