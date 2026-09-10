# Zombie Master: Reborn

This guide covers the `zmrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A staged Zombie Master: Reborn content tree under `<install_dir>/zombie_master_reborn/`

## Support Status

`zmrserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the
generic Source SDK Base 2013 Dedicated Server scaffold from anonymous SteamCMD,
but the real `zombie_master_reborn/` payload still has to be staged locally.
This checked-in support state is validated against the documented Ubuntu 24.04
Linux baseline, and the current GitHub integration lane still exercises both
process and Docker runtime selection around that BYO prerequisite.

## Quick Start

Create the server:

```bash
alphagsm myzmrserve create zmrserver
```

Run setup:

```bash
alphagsm myzmrserve setup
```

Start it:

```bash
alphagsm myzmrserve start
```

Check it:

```bash
alphagsm myzmrserve status
```

Stop it:

```bash
alphagsm myzmrserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Before `start`, stage the full Zombie Master: Reborn tree so
`<install_dir>/zombie_master_reborn/maps/zm_docksofthedead.bsp` exists. If
`setup` or `start` reports an `ENABLED (BYO)` requirement, the public app
`244310` scaffold is still missing the actual mod payload.

## Useful Commands

```bash
alphagsm myzmrserve update
alphagsm myzmrserve backup
```

## Notes

- Module name: `zmrserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create zmrserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `zm_docksofthedead`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Zombie Master: Reborn`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `244310`
- **SteamCMD App Name**: `Source SDK Base 2013 Dedicated Server`

### Server Configuration

- **Config file**: `zombie_master_reborn/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `zm_docksofthedead`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/zmrserver/](../server-templates/zmrserver/)

### Maps and Mods

- **Map directory**: `zombie_master_reborn/maps/`
- **Mod directory**: `zombie_master_reborn/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/zombie_master_reborn/`.
- **Current status**: Supported in `ENABLED (BYO)` mode. Anonymous SteamCMD app `244310` only provides the generic Source SDK 2013 dedicated server scaffold, so stage the real `zombie_master_reborn/` content tree before retrying startup.
- **Map install**: Copy `.bsp` files into `zombie_master_reborn/maps/` and add to `zombie_master_reborn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `zombie_master_reborn/addons/`.
