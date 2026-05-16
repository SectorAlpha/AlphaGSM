# NS2: Combat

This guide covers the `ns2cserver` module in AlphaGSM.

## Requirements

- `screen`
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
- AlphaGSM probes `query` and `info` over A2S on the main game port
- Web admin is enabled by default on `httpport` `8080`

## Developer Notes

### Run File

- **Executable**: `ia32/ns2combatserver_linux32`
- **Location**: `<install_dir>/ia32/ns2combatserver_linux32`
- **Engine**: Spark
- **SteamCMD App ID**: `313900`

### Server Configuration

- **Config path**: `<install_dir>/<server_name>/`
- **Workshop storage**: `<install_dir>/<server_name>/Workshop`
- **Key settings**:
  - `port` — Game port (default: `27015`)
  - `httpport` — Web admin port (default: `8080`)
  - `maxplayers` — Maximum players (default: `24`)
  - `startmap` — Starting map (default: `co_core`)

### Maps and Mods

- **Map selection**: via `startmap`
- **Mod directory**: `<install_dir>/<server_name>/Workshop`
- **Workshop support**: manual storage path only in this first AlphaGSM slice