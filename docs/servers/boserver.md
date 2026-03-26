# Ballistic Overkill

This guide covers the `boserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myboserver create boserver
```

Run setup:

```bash
alphagsm myboserver setup
```

Start it:

```bash
alphagsm myboserver start
```

Check it:

```bash
alphagsm myboserver status
```

Stop it:

```bash
alphagsm myboserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myboserver update
alphagsm myboserver backup
```

## Notes

- Module name: `boserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BODS.x86_64`
- **Location**: `<install_dir>/BODS.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `416881`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `16`
- **Template**: See [server-templates/boserver/](../server-templates/boserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
