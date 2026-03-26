# Silica

This guide covers the `silicaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysilicase create silicaserver
```

Run setup:

```bash
alphagsm mysilicase setup
```

Start it:

```bash
alphagsm mysilicase start
```

Check it:

```bash
alphagsm mysilicase status
```

Stop it:

```bash
alphagsm mysilicase stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysilicase update
alphagsm mysilicase backup
```

## Notes

- Module name: `silicaserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Silica.x86_64`
- **Location**: `<install_dir>/Silica.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2738040`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/silicaserver/](../server-templates/silicaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
