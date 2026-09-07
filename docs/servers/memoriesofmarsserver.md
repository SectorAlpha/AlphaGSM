# Memories of Mars

This guide covers the `memoriesofmarsserver` module in AlphaGSM.

`memoriesofmarsserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymemories create memoriesofmarsserver
```

Run setup:

```bash
alphagsm mymemories setup
```

Start it:

```bash
alphagsm mymemories start
```

Check it:

```bash
alphagsm mymemories status
```

Stop it:

```bash
alphagsm mymemories stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymemories update
alphagsm mymemories backup
```

## Notes

- Module name: `memoriesofmarsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `MemoriesOfMarsServer.sh`
- **Location**: `<install_dir>/MemoriesOfMarsServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `897590`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/memoriesofmarsserver/](../server-templates/memoriesofmarsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
