# Craftopia

This guide covers the `craftopiaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycraftopi create craftopiaserver
```

Run setup:

```bash
alphagsm mycraftopi setup
```

Start it:

```bash
alphagsm mycraftopi start
```

Check it:

```bash
alphagsm mycraftopi status
```

Stop it:

```bash
alphagsm mycraftopi stop
```

## Setup Details

Setup configures:

- the game port (default 8787)
- the install directory
- a generated `ServerSetting.ini` with the selected world name, max player count, and save path
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycraftopi update
alphagsm mycraftopi backup
```

## Notes

- Module name: `craftopiaserver`
- Default port: 8787
- AlphaGSM seeds `ServerSetting.ini` because the Linux dedicated server reads its actual host settings from the ini file rather than the CLI flags
- AlphaGSM `query` and `info` use generic UDP reachability on the main game port

## Developer Notes

### Run File

- **Executable**: `Craftopia.x86_64`
- **Location**: `<install_dir>/Craftopia.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1670340`

### Server Configuration

- **Config file**: `ServerSetting.ini`
- **Max players**: `8`
- **Save directory**: `DedicatedServerSave/`
- **Template**: See [server-templates/craftopiaserver/](../server-templates/craftopiaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
