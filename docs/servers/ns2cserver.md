# NS2: Combat

This guide covers the `ns2cserver` module in AlphaGSM.

The checked-in NS2: Combat lifecycle is wired for both process and Docker
runtimes on the documented Ubuntu 24.04 Linux baseline. Its corrected
launch/A2S contract is pending replacement GitHub validation, so no new
`PASSED` tracker result is recorded for this change.

## Requirements

- Process runtime: `screen`
- Docker runtime: Docker and the shared `steamcmd-linux` runtime image
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myns2c create ns2cserver
```

Run setup:

```bash
alphagsm myns2c setup
```

Start it:

```bash
alphagsm myns2c start
```

Check it:

```bash
alphagsm myns2c status
alphagsm myns2c query
alphagsm myns2c info
```

Stop it:

```bash
alphagsm myns2c stop
```

## Setup Details

Setup configures:

- the game port (default `27015`)
- the install directory
- SteamCMD downloads the server files
- a per-instance config directory at `<install_dir>/<server_name>/`
- a workshop storage directory at `<install_dir>/<server_name>/Workshop`
- managed claims for game UDP, `game + 1` UDP, and web-admin TCP

## Useful Commands

```bash
alphagsm myns2c update
alphagsm myns2c backup
```

## Notes

- Module name: `ns2cserver`
- Game: NS2: Combat
- Engine: Spark
- SteamCMD App ID: `313900`
- Executable: `<install_dir>/ia32/ns2combatserver_linux32`
- Default map: `co_core`
- Process and Docker launch identical game argv as
  `./ns2combatserver_linux32` from `<install_dir>/ia32`, which preserves the
  executable's `../bin/ship` dependency lookup
- AlphaGSM probes exact runtime-resolved A2S on `game port + 1`
- Web admin is enabled by default on `httpport` `8080`
- Current correction status: replacement GitHub validation pending

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ns2cserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `httppassword` | — | string | Web admin password. |
| `httpport` | — | integer | Web admin port. |
| `httpuser` | — | string | Web admin username. |
| `maxplayers` | users | integer | Maximum allowed players. |
| `port` | gameport | integer | Primary gameplay port. |
| `servername` | hostname, name | string | The advertised server name. |
| `startmap` | map, gamemap, level, world | string | Startup map. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `ia32/ns2combatserver_linux32`
- **Location**: `<install_dir>/ia32/ns2combatserver_linux32`
- **Working directory**: `<install_dir>/ia32`
- **Launch path**: `./ns2combatserver_linux32`
- **Engine**: Spark
- **SteamCMD App ID**: `313900`

### Server Configuration

- **Config path**: `<install_dir>/<server_name>/`
- **Workshop storage**: `<install_dir>/<server_name>/Workshop`
- **Runtime argv paths**: `../<server_name>` and
  `../<server_name>/Workshop`
- **Key settings**:
  - `port` — Game port (default: `27015`)
  - `httpport` — Web admin port (default: `8080`)
  - `maxplayers` — Maximum players (default: `24`)
  - `startmap` — Starting map (default: `co_core`)

### Maps and Mods

- **Map selection**: via `startmap`
- **Mod directory**: `<install_dir>/<server_name>/Workshop`
- **Workshop support**: manual storage path only in this first AlphaGSM slice
