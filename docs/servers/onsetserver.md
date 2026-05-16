# Onset

This guide covers the `onsetserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime dependencies
- `openssl` on Linux hosts, matching the upstream Onset dedicated-server guide
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myonset create onsetserver
```

Run setup:

```bash
alphagsm myonset setup
```

Start it:

```bash
alphagsm myonset start
```

Check it:

```bash
alphagsm myonset status
alphagsm myonset query
alphagsm myonset info
```

Stop it:

```bash
alphagsm myonset stop
```

## Setup Details

Setup configures:

- the main game port (default `7777`)
- the install directory
- SteamCMD downloads the server files
- a generated `server_config.json`
- the documented derived ports:
  - query `UDP`: `port - 1`
  - file / HTTP `TCP`: `port - 2`

## Useful Commands

```bash
alphagsm myonset update
alphagsm myonset backup
```

## Notes

- Module name: `onsetserver`
- Game: Onset
- Engine: Unreal 4
- SteamCMD App ID: `1204170`
- Default executable: `<install_dir>/start_linux.sh`
- Config file: `<install_dir>/server_config.json`
- AlphaGSM starts the server with `--config <install_dir>/server_config.json`
- AlphaGSM probes `query` and `info` over A2S on `port - 1`, following the upstream Valve server-query documentation reference
- The generated config defaults to the documented `sandbox` package and a private `masterlist=false` profile

## Developer Notes

### Run File

- **Executable**: `start_linux.sh`
- **Location**: `<install_dir>/start_linux.sh`
- **SteamCMD App ID**: `1204170`

### Server Configuration

- **Config path**: `<install_dir>/server_config.json`
- **Key settings**:
  - `servername`
  - `servername_short`
  - `gamemode`
  - `ipaddress`
  - `port`
  - `maxplayers`
  - `password`
  - `timeout`
  - `iplimit`

### Ports

- **Game**: `port/udp`
- **Query**: `port - 1/udp`
- **HTTP / file downloads**: `port - 2/tcp`