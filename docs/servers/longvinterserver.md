# Longvinter

This guide covers the `longvinterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylongvint create longvinterserver
```

Run setup:

```bash
alphagsm mylongvint setup
```

Start it:

```bash
alphagsm mylongvint start
```

Check it:

```bash
alphagsm mylongvint status
```

Stop it:

```bash
alphagsm mylongvint stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylongvint update
alphagsm mylongvint backup
```

## Notes

- Module name: `longvinterserver`
- Default port: 7777
- Current CI status: disabled. The current SteamCMD build crashes during startup
	with missing `BlueprintableOnlineBeacons` and `DiscordRpc` packaged script
	dependencies before either the game port or query port opens.

## Developer Notes

### Run File

- **Executable**: `LongvinterServer.sh`
- **Location**: `<install_dir>/LongvinterServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1639880`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/longvinterserver/](../server-templates/longvinterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
