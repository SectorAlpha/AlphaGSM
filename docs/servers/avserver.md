# Avorion

This guide covers the `avserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myavserver create avserver
```

Run setup:

```bash
alphagsm myavserver setup
```

Start it:

```bash
alphagsm myavserver start
```

Check it:

```bash
alphagsm myavserver status
```

Stop it:

```bash
alphagsm myavserver stop
```

## Setup Details

Setup configures:

- the game port (default 27000)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myavserver update
alphagsm myavserver backup
```

## Notes

- Module name: `avserver`
- Default port: 27000

## Developer Notes

### Run File

- **Executable**: `server.sh`
- **Location**: `<install_dir>/server.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `565060`

### Server Configuration

- **Config files**: `admin.xml`
- **Template**: See [server-templates/avserver/](../server-templates/avserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
