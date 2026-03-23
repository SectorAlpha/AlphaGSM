# The Isle

This guide covers the `tiserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytiserver create tiserver
```

Run setup:

```bash
alphagsm mytiserver setup
```

Start it:

```bash
alphagsm mytiserver start
```

Check it:

```bash
alphagsm mytiserver status
```

Stop it:

```bash
alphagsm mytiserver stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mytiserver update
alphagsm mytiserver backup
```

## Notes

- Module name: `tiserver`
- Default port: 7778

## Developer Notes

### Run File

- **Executable**: `TheIsleServer.sh`
- **Location**: `<install_dir>/TheIsleServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `412680`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/tiserver/](../server-templates/tiserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
