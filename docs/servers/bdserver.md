# Base Defense

This guide covers the `bdserver` module in AlphaGSM.

`bdserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub continues to exercise process and Docker lanes; both use the
same shared Valve A2S query hook.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybdserver create bdserver
```

Run setup:

```bash
alphagsm mybdserver setup
```

Start it:

```bash
alphagsm mybdserver start
```

Check it:

```bash
alphagsm mybdserver status
```

Stop it:

```bash
alphagsm mybdserver stop
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
alphagsm mybdserver update
alphagsm mybdserver backup
```

## Notes

- Module name: `bdserver`
- Docker readiness uses AlphaGSM `info --json` with the runtime-resolved A2S
  host rather than a host-only `screen` log.
- Replacement GitHub CI validation of this shared query-host correction is pending.
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create bdserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `pve_tomb`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `3`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Base Defense`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `817300`

### Server Configuration

- **Config file**: `bdef/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `pve_tomb`
- **Max players**: `3`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/bdserver/](../server-templates/bdserver/)

### Maps and Mods

- **Map directory**: `bdef/maps/`
- **Mod directory**: `bdef/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `bdef/maps/` and add to `bdef/mapcycle.txt`.
- **Mod install**: Use Metamod in `bdef/dlls/` or AMX Mod X in `bdef/addons/amxmodx/`.
