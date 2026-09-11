# Nuclear Dawn

This guide covers the `ndserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A staged Nuclear Dawn content tree under `<install_dir>/nucleardawn/`

## Support Status

`ndserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the
anonymous dedicated-server scaffold, but the current public payload still lacks
the full Nuclear Dawn game content needed for a working server. This checked-in
support state is validated against the documented Ubuntu 24.04 Linux baseline,
and the current GitHub integration lane still exercises both process and
Docker runtime selection around that staged-content prerequisite.

## Quick Start

Create the server:

```bash
alphagsm myndserver create ndserver
```

Run setup:

```bash
alphagsm myndserver setup
```

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

Before `start`, stage the full Nuclear Dawn tree so
`<install_dir>/nucleardawn/maps/hydro.bsp` exists. If `setup` or `start`
reports an `ENABLED (BYO)` requirement, the anonymous dedicated payload is still
missing the actual game content.

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
- **Current status**: Supported in `ENABLED (BYO)` mode. The anonymous dedicated-server app still installs only a partial `nucleardawn/` tree, so stage the real game content before retrying startup.
- **Map install**: Copy `.bsp` files into `nucleardawn/maps/` and add to `nucleardawn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nucleardawn/addons/`.
