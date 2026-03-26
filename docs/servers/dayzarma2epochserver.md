# DayZ Arma 2 Epoch

This guide covers the `dayzarma2epochserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayzarma create dayzarma2epochserver
```

Run setup:

```bash
alphagsm mydayzarma setup
```

Start it:

```bash
alphagsm mydayzarma start
```

Check it:

```bash
alphagsm mydayzarma status
```

Stop it:

```bash
alphagsm mydayzarma stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayzarma update
alphagsm mydayzarma backup
```

## Notes

- Module name: `dayzarma2epochserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `arma2oaserver`
- **Location**: `<install_dir>/arma2oaserver`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `33935`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/dayzarma2epochserver/](../server-templates/dayzarma2epochserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
