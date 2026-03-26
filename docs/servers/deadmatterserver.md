# Dead Matter

This guide covers the `deadmatterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydeadmatt create deadmatterserver
```

Run setup:

```bash
alphagsm mydeadmatt setup
```

Start it:

```bash
alphagsm mydeadmatt start
```

Check it:

```bash
alphagsm mydeadmatt status
```

Stop it:

```bash
alphagsm mydeadmatt stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydeadmatt update
alphagsm mydeadmatt backup
```

## Notes

- Module name: `deadmatterserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DeadMatterServer.sh`
- **Location**: `<install_dir>/DeadMatterServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1110990`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/deadmatterserver/](../server-templates/deadmatterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
