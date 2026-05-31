# Wreckfest

This guide covers the `wreckfestserver` module in AlphaGSM.

Status: `PASSED` on 2026-05-31.

## Requirements

- Docker
- AlphaGSM's `wine-proton` runtime image on Linux
- SteamCMD access for app `361580` with anonymous login

## Quick Start

Create the server:

```bash
alphagsm mywreckfes create wreckfestserver
```

Run setup:

```bash
alphagsm mywreckfes setup
```

Start it:

```bash
alphagsm mywreckfes start
```

Check it:

```bash
alphagsm mywreckfes status
alphagsm mywreckfes query
alphagsm mywreckfes info --json
```

Stop it:

```bash
alphagsm mywreckfes stop
```

## Setup Details

Setup configures:

- the main game port (default `33540`)
- the Steam query port (default `27016`)
- the Steam networking port (default `27015`)
- the install directory
- the managed `server_config.cfg`

On Linux, AlphaGSM downloads the Windows dedicated payload for app `361580`,
launches `Wreckfest_x64.exe` through the shared Docker `wine-proton` runtime,
and seeds `server_config.cfg` from the vendor `initial_server_config.cfg` when
needed.

## Useful Commands

```bash
alphagsm mywreckfes update
alphagsm mywreckfes backup
alphagsm mywreckfes set port 33541
alphagsm mywreckfes set queryport 27017
alphagsm mywreckfes set steamport 27018
alphagsm mywreckfes set servername "AlphaGSM Wreckfest"
alphagsm mywreckfes set maxplayers 16
```

AlphaGSM keeps these upstream config keys in sync inside `server_config.cfg`:

- `game_port`
- `query_port`
- `steam_port`
- `server_name`
- `password`
- `max_players`

## Notes

- Module name: `wreckfestserver`
- Main game port default: `33540`
- Query/info contract on validated Linux lane: generic `tcp` on the managed main game port

## Developer Notes

### Run File

- **Executable**: `Wreckfest_x64.exe`
- **Fallback executable**: `Wreckfest.exe`
- **Location**: `<install_dir>/Wreckfest_x64.exe`
- **Runtime**: Docker `wine-proton` on Linux
- **SteamCMD App ID**: `361580`

### Server Configuration

- **Config file**: `server_config.cfg`
- **Vendor seed file**: `initial_server_config.cfg`
- **Template**: See [server-templates/wreckfestserver/server_config.cfg](../server-templates/wreckfestserver/server_config.cfg)

### Maps and Mods

- **Map rotation**: configure through `server_config.cfg`
- **Mod directory**: `<install_dir>/mods/`
- **Workshop support**: use Wreckfest's native mod loading rules
