# Mordhau

This guide covers the `mordserver` module in AlphaGSM.

`mordserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymordserv create mordserver
```

Run setup:

```bash
alphagsm mymordserv setup
```

Start it:

```bash
alphagsm mymordserv start
```

Check it:

```bash
alphagsm mymordserv status
```

Stop it:

```bash
alphagsm mymordserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymordserv update
alphagsm mymordserv backup
```

## Notes

- Module name: `mordserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `MordhauServer.sh`
- **Location**: `<install_dir>/MordhauServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `629800`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/mordserver/](../server-templates/mordserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
