# Vampire Slayer

This guide covers the `vsserver` module in AlphaGSM.

`vsserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that owned-mod-content prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvsserver create vsserver
```

Run setup:

```bash
alphagsm myvsserver setup
```

`vsserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the base
HLDS runtime through SteamCMD, but Steam app `90` does not provide the Vampire
Slayer mod payload. Before `start`, copy a complete owned Vampire Slayer
content tree into `<install_dir>/vs/` so
`<install_dir>/vs/maps/vs_frost.bsp` exists.

Start it:

```bash
alphagsm myvsserver start
```

Check it:

```bash
alphagsm myvsserver status
```

Stop it:

```bash
alphagsm myvsserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Suggested flow:

```bash
alphagsm myvsserver create vsserver
alphagsm myvsserver setup -n 27015 /path/to/vsserver
# copy the full Vampire Slayer mod tree into /path/to/vsserver/vs/
alphagsm myvsserver start
```

## Useful Commands

```bash
alphagsm myvsserver update
alphagsm myvsserver backup
```

## Notes

- Module name: `vsserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create vsserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `vs_frost`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Vampire Slayer`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `vs/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `vs_frost`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/vsserver/](../server-templates/vsserver/)

### Maps and Mods

- **Map directory**: `vs/maps/`
- **Mod directory**: `vs/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `vs/maps/` and add to `vs/mapcycle.txt`.
- **Mod install**: Use Metamod in `vs/dlls/` or AMX Mod X in `vs/addons/amxmodx/`.
