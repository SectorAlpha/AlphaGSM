# Exfil

This guide covers the `exfilserver` module in AlphaGSM.

`exfilserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Docker runs the server as the invoking host user because the executable rejects root.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myexfilser create exfilserver
```

Run setup:

```bash
alphagsm myexfilser setup
```

Start it:

```bash
alphagsm myexfilser start
```

Check it:

```bash
alphagsm myexfilser status
```

Stop it:

```bash
alphagsm myexfilser stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myexfilser update
alphagsm myexfilser backup
```

## Notes

- Module name: `exfilserver`
- Default game port: 7777
- Default query port: 27015
- `query`, `info`, and `info --json` use the validated TCP health surface on
  the managed game port.

## Developer Notes

### Run File

- **Executable**: `ExfilServer.sh`
- **Location**: `<install_dir>/ExfilServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3093190`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/exfilserver/](../server-templates/exfilserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
