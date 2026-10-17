# SourceForts Classic

This guide covers the `sfcserver` module in AlphaGSM.

`sfcserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that staged-ModDB-content prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- The official SourceForts Classic 1.0 RC7 (Fix) 7z from ModDB, extracted under `<install_dir>/sfclassic/`

## Support Status

`sfcserver` is supported in `ENABLED (BYO)` mode. AlphaGSM installs Steam app
`244310` from the anonymous `previous2021` branch. That legacy SDK 2013
dedicated branch is the 32-bit launcher this game can start. The public branch
of the same app does not finish startup. The install still needs the official
SourceForts Classic 1.0 RC7 (Fix) tree from ModDB. Leave the 1.1b3 Linux64
pre-release unstaged; this depot does not ship `srcds_linux64`. App `244310`
publishes `bin/*_srv.so`. `prestart` copies those onto the unsuffixed names
`srcds_linux` loads, restores the launcher execute bit, and writes
`sv_hibernate_when_empty 0`. A local process start answered A2S on UDP 58844
(map `sf_astrodome`, 0/32). The A2S hostname was `Sourceforts Classic 1.0 [BUILD]`.
The process was stopped and that UDP port was free. Docker was not run.

## Quick Start

Create the server:

```bash
alphagsm mysfcserve create sfcserver
```

Run setup:

```bash
alphagsm mysfcserve setup
```

Start it:

```bash
alphagsm mysfcserve start
```

Check it:

```bash
alphagsm mysfcserve status
```

Stop it:

```bash
alphagsm mysfcserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Before `start`, download SourceForts Classic 1.0 RC7 (Fix) from
[the official ModDB file page](https://www.moddb.com/mods/sourceforts/downloads/sourceforts-classic-10-release-candidate-7-fix-7z)
and extract the resulting `sfclassic/` tree so
`<install_dir>/sfclassic/maps/sf_astrodome.bsp` exists. If `setup` or `start`
reports an `ENABLED (BYO)` requirement, app `244310` on `previous2021` is still
only the SDK scaffold.

## Useful Commands

```bash
alphagsm mysfcserve update
alphagsm mysfcserve backup
```

## Notes

- Module name: `sfcserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create sfcserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `sf_astrodome`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM SourceForts Classic`. |
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

- **Config file**: `sfclassic/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `sf_astrodome`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/sfcserver/](../server-templates/sfcserver/)

### Maps and Mods

- **Map directory**: `sfclassic/maps/`
- **Mod directory**: `sfclassic/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/sfclassic/`.
- **Current status**: Supported in `ENABLED (BYO)` mode. Anonymous SteamCMD app `244310` on `previous2021` provides the 32-bit SDK scaffold, and the official ModDB 1.0 RC7 (Fix) tree provides `sfclassic/`. Local process A2S was validated on UDP 58844 (map `sf_astrodome`, 0/32) and the server was stopped. Docker was not rerun.
- **Map install**: Copy `.bsp` files into `sfclassic/maps/` and add to `sfclassic/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `sfclassic/addons/`.

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
This helper checks known sentinels only and directs you to stage the complete
compatible distribution manually; managed import is unavailable for this recipe.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
