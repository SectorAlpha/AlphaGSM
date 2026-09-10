# Blade Symphony

This guide covers the `bsserver` module in AlphaGSM.

## Status

`bsserver` is currently `ENABLED (AUTH)`.

Before `start`, authenticate Steam or SteamCMD with an account entitled to
Blade Symphony so the shared `berimbau` content depot installs alongside the
dedicated server tool.

## Requirements

- Docker or a compatible local runtime for the `steamcmd-linux` family
- SteamCMD runtime libraries when using the host/process lane
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybsserver create bsserver
```

Run setup:

```bash
alphagsm mybsserver setup
```

If anonymous setup finishes but `start` reports that `berimbau/GameInfo.txt` is
missing, install with authenticated Steam or SteamCMD access for an owned Blade
Symphony account, or stage a full owned `berimbau/` content tree into the
install directory before starting again.

Start it:

```bash
alphagsm mybsserver start
```

Check it:

```bash
alphagsm mybsserver status
```

Stop it:

```bash
alphagsm mybsserver stop
```

## Setup Details

Setup configures:

- the game port (default `27015`)
- the install directory
- the executable name
- SteamCMD downloads the dedicated server tool app `228780`

Authenticated installs may still need the owned Blade Symphony app content so
the shared depot that contains `berimbau/GameInfo.txt` and the wider
`berimbau/` content tree is present.

## Useful Commands

```bash
alphagsm mybsserver update
alphagsm mybsserver backup
```

## Notes

- Module name: `bsserver`
- Default port: `27015`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create bsserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `duel_winter`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Blade Symphony`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `bin/srcds_run.sh`
- **Location**: `<install_dir>/bin/srcds_run.sh`
- **Engine**: Source
- **SteamCMD App ID**: `228780`

### Server Configuration

- **Config file**: `berimbau/cfg/server.cfg`
- **Key settings**:
  - `hostname` - Server name
  - `rcon_password` - Remote console password
  - `sv_password` - Join password
- **Default port**: `27015`
- **Default map**: `duel_winter`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)

### Maps and Mods

- **Map directory**: `berimbau/maps/`
- **Mod directory**: `berimbau/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM supports `manifest`, direct archive `url`,
  `gamebanana`, and `moddb` addon sources for this server through the shared
  Source addon flow once the owned `berimbau` content tree is present.
