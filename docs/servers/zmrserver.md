# Zombie Master: Reborn

This guide covers the `zmrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- The official Zombie Master: Reborn Beta 6 Linux archive, `zombie_master_reborn_b6_1.tar.gz`, linked from [zombiemaster.dev](https://zombiemaster.dev/), extracted under `<install_dir>/zombie_master_reborn/`

## Support Status

`zmrserver` is supported in `ENABLED (BYO)` mode. AlphaGSM installs Steam app
`244310` from the anonymous `previous2021` branch. That legacy SDK 2013
dedicated branch is the 32-bit launcher this game can start. The public branch
of the same app does not finish startup. The install still needs the official
Linux archive linked from the project page. App `244310` publishes
`bin/*_srv.so`. `prestart` copies those onto the unsuffixed names `srcds_linux`
loads, restores the launcher execute bit, and writes `sv_hibernate_when_empty 0`.
This dedicated build reports that cvar as an unknown command. A local process
start still answered A2S on UDP 42202 (map `zm_docksofthedead`, 0/16).
The A2S hostname was `AlphaGSM Zombie Master: Reborn`. The process was stopped
and that UDP port was free. Docker was not run.

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

Before `start`, download the Linux archive linked from
[the official project page](https://zombiemaster.dev/) and extract the resulting
`zombie_master_reborn/` tree so
`<install_dir>/zombie_master_reborn/maps/zm_docksofthedead.bsp` exists. Keep
every multiplayer map. If `setup` or `start` reports an `ENABLED (BYO)`
requirement, app `244310` on `previous2021` is still only the SDK scaffold.

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
- **SteamCMD branch**: `previous2021`
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
- **Current status**: Supported in `ENABLED (BYO)` mode. Anonymous SteamCMD app `244310` on `previous2021` provides the 32-bit SDK scaffold, and the official Linux archive linked from the project page provides `zombie_master_reborn/`. Local process A2S was validated on UDP 42202 (map `zm_docksofthedead`, 0/16) and the server was stopped. Docker was not run.
- **Map install**: Copy `.bsp` files into `zombie_master_reborn/maps/` and add to `zombie_master_reborn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `zombie_master_reborn/addons/`.

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
This helper checks known sentinels only and directs you to stage the complete
compatible distribution manually; managed import is unavailable for this recipe.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
