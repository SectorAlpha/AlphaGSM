# Nuclear Dawn

This guide covers the `ndserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A staged Nuclear Dawn content tree under `<install_dir>/nucleardawn/`
- Or an entitled Steam profile for dedicated server app `111710`

## Support Status

`ndserver` is supported in `ENABLED (BYO)` mode. Setup with no saved profile
still installs Steam app `111710` anonymously. That public payload is only a
partial tree and does not provide `nucleardawn/maps/hydro.bsp`. Setup with
`--auth-profile NAME` downloads app `111710` through that profile and does not
fall back to anonymous. This checked-in support state is validated against the
documented Ubuntu 24.04 Linux baseline, and the current GitHub integration lane
still exercises both process and Docker runtime selection around that
content prerequisite.

## Quick Start

Create the server:

```bash
alphagsm myndserver create ndserver
```

Run setup. Without a profile this stays anonymous. For an owned copy:

```bash
alphagsm steam-auth login owned your_steam_username
alphagsm myndserver setup --auth-profile owned
```

Enter credentials only at the local SteamCMD prompts. A later setup keeps the
saved profile name when one is stored. A local process install with profile
`owned` supplied app `111710`, including `nucleardawn/maps/hydro.bsp`. The
NTFS install omitted the execute bit on `srcds_linux`, so the first start
exited before A2S; `prestart` now restores that bit. After that, the same
install answered A2S on UDP 36736 (hostname AlphaGSM Nuclear Dawn, map
`hydro`, 0/32). The process was stopped and that UDP port was free. Docker
was not run. UDP 27015 was left to an unrelated Left 4 Dead 2 server.

Start it:

```bash
alphagsm myndserver start
```

Check it:

```bash
alphagsm myndserver status
```

Stop it:

```bash
alphagsm myndserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Before `start`, `<install_dir>/nucleardawn/maps/hydro.bsp` must exist. An
entitled `--auth-profile` install of app `111710` supplies it. Anonymous setup
does not. You can still copy a complete owned tree into
`<install_dir>/nucleardawn/` instead. If `setup` or `start` reports an
`ENABLED (BYO)` requirement, the dedicated payload is still missing the game
content.

## Useful Commands

```bash
alphagsm myndserver update
alphagsm myndserver backup
```

## Notes

- Module name: `ndserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ndserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `hydro`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Nuclear Dawn`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `111710`
- **SteamCMD App Name**: `Nuclear Dawn - Dedicated Server`

### Server Configuration

- **Config file**: `nucleardawn/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `hydro`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/ndserver/](../server-templates/ndserver/)

### Maps and Mods

- **Map directory**: `nucleardawn/maps/`
- **Mod directory**: `nucleardawn/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/nucleardawn/`.
- **Current status**: Supported in `ENABLED (BYO)` mode. Anonymous app `111710` still installs only a partial `nucleardawn/` tree. An entitled `--auth-profile` install of the same app does not fall back to anonymous. The dedicated server stays awake (`sv_hibernate_when_empty 0`) so query and info use Source A2S.
- **Map install**: Copy `.bsp` files into `nucleardawn/maps/` and add to `nucleardawn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nucleardawn/addons/`.

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
The managed recipe has one SteamCMD source, app `111710`, for an entitled
profile. Anonymous setup does not use that source. File checks do not establish
game readiness. See [BYO files and private SteamCMD acquisition](../byo-files.md).
