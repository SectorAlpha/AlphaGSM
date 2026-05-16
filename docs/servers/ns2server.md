# Natural Selection 2

This guide covers the `ns2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myns2 create ns2server
```

Run setup:

```bash
alphagsm myns2 setup
```

Start it:

```bash
alphagsm myns2 start
```

Check it:

```bash
alphagsm myns2 status
alphagsm myns2 query
alphagsm myns2 info
```

Stop it:

```bash
alphagsm myns2 stop
```

## Setup Details

Setup configures:

- the game port (default `27015`)
- the install directory
- SteamCMD downloads the server files
- a per-instance config directory at `<install_dir>/<server_name>/`
- a workshop storage directory at `<install_dir>/<server_name>/Workshop`
- a managed log directory at `<install_dir>/logs`

## Useful Commands

```bash
alphagsm myns2 update
alphagsm myns2 backup
```

## Notes

- Module name: `ns2server`
- Game: Natural Selection 2
- Engine: Spark
- SteamCMD App ID: `4940`
- Executable: `<install_dir>/x64/server_linux`
- Default map: `ns2_summit`
- AlphaGSM probes `query` and `info` over A2S on the main game port
- Web admin is enabled by default on `httpport` `8080`
- Mod server is enabled by default on `modserverport` `27031`

## Developer Notes

### Run File

- **Executable**: `x64/server_linux`
- **Location**: `<install_dir>/x64/server_linux`
- **Engine**: Spark
- **SteamCMD App ID**: `4940`

### Server Configuration

- **Config path**: `<install_dir>/<server_name>/`
- **Workshop storage**: `<install_dir>/<server_name>/Workshop`
- **Log directory**: `<install_dir>/logs`
- **Key settings**:
  - `port` — Game port (default: `27015`)
  - `httpport` — Web admin port (default: `8080`)
  - `modserverport` — Mod server port (default: `27031`)
  - `maxplayers` — Maximum players (default: `20`)
  - `maxspectators` — Maximum spectators (default: `5`)
  - `startmap` — Starting map (default: `ns2_summit`)

### Maps and Mods

- **Map selection**: via `startmap`
- **Mod directory**: `<install_dir>/<server_name>/Workshop`
- **Workshop support**: manual storage path only in this first AlphaGSM slice