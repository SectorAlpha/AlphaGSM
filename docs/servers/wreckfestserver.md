# Wreckfest

This guide covers the `wreckfestserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

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
```

Stop it:

```bash
alphagsm mywreckfes stop
```

## Setup Details

Setup configures:

- the game port (default 33540)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywreckfes update
alphagsm mywreckfes backup
alphagsm mywreckfes set port 33541
```

`set port` rewrites `server_config.cfg` immediately through the schema-backed config-sync path. The shared alias layer also accepts `gameport` for this module.

## Notes

- Module name: `wreckfestserver`
- Default port: 33540

## Developer Notes

### Run File

- **Executable**: `WreckfestServer`
- **Location**: `<install_dir>/WreckfestServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `361580`

### Server Configuration

- **Config file**: `server_config.cfg`
- **Template**: See [server-templates/wreckfestserver/](../server-templates/wreckfestserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `server_port=` aligned with `set port`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
