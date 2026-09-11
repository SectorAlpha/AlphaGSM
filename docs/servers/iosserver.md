# IOSoccer

This guide covers the `iosserver` module in AlphaGSM.

`iosserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04 Linux
baseline. GitHub keeps one Docker-default auth-gated lifecycle entry; it does
not attempt the known-crashing public branch as a process test.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myiosserve create iosserver
```

Run setup:

```bash
alphagsm myiosserve setup
```

Start it:

```bash
alphagsm myiosserve start
```

Check it:

```bash
alphagsm myiosserve status
```

Stop it:

```bash
alphagsm myiosserve stop
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
alphagsm myiosserve update
alphagsm myiosserve backup
```

## Notes

- Module name: `iosserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create iosserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `8v8_vienna`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM IOSoccer`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `673990`

Current validation status: `ENABLED (AUTH)`. AlphaGSM targets the dedicated
tool app `673990`, but the supported sdk2013 branches `iosoccer2025` / `beta`
are not anonymously accessible. Fresh SteamCMD probes against the dedicated
tool app still return `ERROR! Failed to set beta 'iosoccer2025'` for anonymous
login, while the public branch continues to crash on Linux after startup. The
supported path is authenticated Steam or SteamCMD access to the dedicated tool
branch before `setup`.

### Server Configuration

- **Config file**: `iosoccer/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `8v8_vienna`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/iosserver/](../server-templates/iosserver/)

### Maps and Mods

- **Map directory**: `iosoccer/maps/`
- **Mod directory**: `iosoccer/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/iosoccer/`.
- **Map install**: Copy `.bsp` files into `iosoccer/maps/` and add to `iosoccer/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `iosoccer/addons/`.
