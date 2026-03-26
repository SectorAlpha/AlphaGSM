# Last Oasis

This guide covers the `lastoasisserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylastoasi create lastoasisserver
```

Run setup:

```bash
alphagsm mylastoasi setup
```

Start it:

```bash
alphagsm mylastoasi start
```

Check it:

```bash
alphagsm mylastoasi status
```

Stop it:

```bash
alphagsm mylastoasi stop
```

## Setup Details

Setup configures:

- the game port (default 15001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylastoasi update
alphagsm mylastoasi backup
```

## Notes

- Module name: `lastoasisserver`
- Default port: 15001

## Developer Notes

### Run File

- **Executable**: `LastOasisServer.x86_64`
- **Location**: `<install_dir>/LastOasisServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `920720`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/lastoasisserver/](../server-templates/lastoasisserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
