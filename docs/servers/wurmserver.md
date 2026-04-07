# Wurm Unlimited

This guide covers the `wurmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywurmserv create wurmserver
```

Run setup:

```bash
alphagsm mywurmserv setup
```

Start it:

```bash
alphagsm mywurmserv start
```

Check it:

```bash
alphagsm mywurmserv status
```

Stop it:

```bash
alphagsm mywurmserv stop
```

## Setup Details

Setup configures:

- the game port (default 3724)
- the world folder to auto-start in headless mode (default `Adventure`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywurmserv update
alphagsm mywurmserv backup
```

## Notes

- Module name: `wurmserver`
- Default port: 3724
- Valid game port range: 1-32767
- Default Steam query port: 27016
- Default RMI ports: 7220 and 7221
- AlphaGSM starts Wurm with `WurmServerLauncher start=<world>` so it skips the interactive setup GUI
- During install AlphaGSM copies `linux64/steamclient.so` into `nativelibs/` because the headless launcher expects a local Steam client library
- During install AlphaGSM seeds root-level `Adventure` and `Creative` world folders from `dist/` on fresh SteamCMD installs
- AlphaGSM `query` and `info` use generic TCP reachability on the game port

## Developer Notes

### Run File

- **Executable**: `WurmServerLauncher`
- **Location**: `<install_dir>/WurmServerLauncher`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `402370`
- **Headless launch**: `./WurmServerLauncher start=Adventure ip=127.0.0.1 externalport=<port> queryport=<queryport> rmiregport=<internalport> rmiport=<rmiport>`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/wurmserver/](../server-templates/wurmserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
