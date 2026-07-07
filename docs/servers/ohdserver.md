# Operation: Harsh Doorstop

This guide covers the `ohdserver` module in AlphaGSM.

`ohdserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime, with A2S `query` /
`info` on the managed `queryport`.

## Requirements

- `docker` for the validated branch-local `steamcmd-linux` runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myohdserve create ohdserver
```

Run setup:

```bash
alphagsm myohdserve setup
```

Start it:

```bash
alphagsm myohdserve start
```

Check it:

```bash
alphagsm myohdserve status
```

Stop it:

```bash
alphagsm myohdserve stop
```

## Setup Details

Setup configures:

- the game port (default `7777`)
- the A2S query port (default `27015`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myohdserve update
alphagsm myohdserve backup
```

## Notes

- Module name: `ohdserver`
- Default port: `7777`
- Default query port: `27015`
- Validated Linux support path: native Linux dedicated payload on the shared `steamcmd-linux` runtime image

## Developer Notes

### Run File

- **Executable**: `HarshDoorstopServer.sh` (falls back to `HarshDoorstop/Binaries/Linux/HarshDoorstopServer-Linux-Shipping` when needed)
- **Location**: `<install_dir>/HarshDoorstopServer.sh`
- **Engine**: native Linux Unreal dedicated server
- **SteamCMD App ID**: `950900`
- **Launch contract**: `HarshDoorstopServer.sh -Port=<port> -QueryPort=<queryport> -log`

### Server Configuration

- **Config files**: runtime launch options plus the upstream Harsh Doorstop payload
- **Health surface**: A2S `query`, `info`, and `info --json` on the managed `queryport`
- **Template**: See [server-templates/ohdserver/](../server-templates/ohdserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
