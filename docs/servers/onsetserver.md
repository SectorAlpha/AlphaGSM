# Onset

This guide covers the `onsetserver` module in AlphaGSM.

## Requirements

The native Linux server requires the legacy OpenSSL 1.1 runtime (`libssl.so.1.1`),
which Ubuntu 24.04 does not include by default. AlphaGSM's `steamcmd-linux` Docker
image includes this dependency.

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
- AlphaGSM adds the install root to `LD_LIBRARY_PATH` so the launcher can load
  the bundled `libsteam_api.so`
- AlphaGSM probes `query` and `info` on the documented HTTP file service at
  `port - 2`, requiring an application-level HTTP response
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
