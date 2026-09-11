# Double Action: Boogaloo

This guide covers the `dabserver` module in AlphaGSM.

## Status

`dabserver` is currently `ENABLED (AUTH)`.

Before `setup` or `start`, authenticate Steam or SteamCMD with an account
entitled to Double Action: Boogaloo so the current app `317360` content can be
staged into the install directory. The retired dedicated tool app `317800`
still crashes on modern Linux, and anonymous SteamCMD for app `317360`
currently returns `No subscription`.

## Requirements

- Docker or a compatible local runtime for the `steamcmd-linux` family
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydabserve create dabserver
```

Run setup:

```bash
alphagsm mydabserve setup
```

If you have not already staged the current Double Action content, setup will
fail fast with `ENABLED (AUTH)` guidance instead of trying to use the retired
anonymous dedicated tool path.

Start it:

```bash
alphagsm mydabserve start
```

Check it:

```bash
alphagsm mydabserve status
```

Stop it:

```bash
alphagsm mydabserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- default configuration and backup settings

AlphaGSM supports two practical paths:

- authenticate Steam or SteamCMD and stage the current Double Action app
  `317360` content before setup/start
- or manually stage a full current content tree containing
  `dab/GameInfo.txt`, `dabds.sh`, and the Linux Source SDK 2013 multiplayer
  server files under `<install_dir>/`

## Useful Commands

```bash
alphagsm mydabserve update
alphagsm mydabserve backup
```

## Notes

- Module name: `dabserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create dabserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `da_rooftops`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `10`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Double Action: Boogaloo`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `dabds.sh`
- **Location**: `<install_dir>/dabds.sh`
- **Engine**: Source
- **SteamCMD App IDs**:
  - retired dedicated tool: `317800`
  - current entitled game content: `317360`

### Server Configuration

- **Config file**: `dab/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `da_rooftops`
- **Max players**: `10`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/dabserver/](../server-templates/dabserver/)

### Maps and Mods

- **Map directory**: `dab/maps/`
- **Mod directory**: `dab/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/dab/`.
- **Map install**: Copy `.bsp` files into `dab/maps/` and add to `dab/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `dab/addons/`.
