# Satisfactory

This guide covers the `satisfactory` module in AlphaGSM.

`satisfactory` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysatisfac create satisfactory
```

Run setup:

```bash
alphagsm mysatisfac setup
```

Start it:

```bash
alphagsm mysatisfac start
```

Check it:

```bash
alphagsm mysatisfac status
```

Stop it:

```bash
alphagsm mysatisfac stop
```

## Setup Details

Setup configures:

- the game port (default 15777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysatisfac update
alphagsm mysatisfac backup
```

## Notes

- Module name: `satisfactory`
- Default port: 15777

## Developer Notes

### Run File

- **Executable**: `FactoryServer.sh`
- **Location**: `<install_dir>/FactoryServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1690800`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/satisfactory/](../server-templates/satisfactory/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
