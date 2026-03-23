# Necesse

This guide covers the `necserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynecserve create necserver
```

Run setup:

```bash
alphagsm mynecserve setup
```

Start it:

```bash
alphagsm mynecserve start
```

Check it:

```bash
alphagsm mynecserve status
```

Stop it:

```bash
alphagsm mynecserve stop
```

## Setup Details

Setup configures:

- the game port (default 14159)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynecserve update
alphagsm mynecserve backup
```

## Notes

- Module name: `necserver`
- Default port: 14159

## Developer Notes

### Run File

- **Executable**: `Server.jar`
- **Location**: `<install_dir>/Server.jar`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1169370`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/necserver/](../server-templates/necserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
