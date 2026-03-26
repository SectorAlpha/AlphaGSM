# SCP: Secret Laboratory

This guide covers the `scpslserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myscpslser create scpslserver
```

Run setup:

```bash
alphagsm myscpslser setup
```

Start it:

```bash
alphagsm myscpslser start
```

Check it:

```bash
alphagsm myscpslser status
```

Stop it:

```bash
alphagsm myscpslser stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myscpslser update
alphagsm myscpslser backup
```

## Notes

- Module name: `scpslserver`
- Default port: 7778

## Developer Notes

### Run File

- **Executable**: `LocalAdmin`
- **Location**: `<install_dir>/LocalAdmin`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `996560`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/scpslserver/](../server-templates/scpslserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
