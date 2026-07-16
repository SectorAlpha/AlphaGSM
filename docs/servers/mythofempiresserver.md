# Myth of Empires

This guide covers the `mythofempiresserver` module in AlphaGSM.

`mythofempiresserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. GitHub validates it through the shared `wine-proton` Docker
runtime; the forced host-Proton lane did not reach its health surface.

## Requirements

- Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymythofem create mythofempiresserver
```

Run setup:

```bash
alphagsm mymythofem setup
```

Start it:

```bash
alphagsm mymythofem start
```

Check it:

```bash
alphagsm mymythofem status
```

Stop it:

```bash
alphagsm mymythofem stop
```

## Setup Details

Setup configures:

- the game port (default 12888)
- the A2S query port (default 12889)
- the install directory
- SteamCMD downloads the server files

The Docker lifecycle uses AlphaGSM's runtime-resolved A2S `info --json`
surface instead of waiting for an install-tree `MOE.log` that is not a valid
manager-container readiness signal.

## Useful Commands

```bash
alphagsm mymythofem update
alphagsm mymythofem backup
```

## Notes

- Module name: `mythofempiresserver`
- Default game port: 12888
- Default query port: 12889
- The Docker-default heavy lane correction is pending replacement GitHub CI validation.

## Developer Notes

### Run File

- **Executable**: `MOE/Binaries/Win64/MOEServer.exe`
- **Location**: `<install_dir>/MOE/Binaries/Win64/MOEServer.exe`
- **Engine**: Windows dedicated server through Wine/Proton
- **SteamCMD App ID**: `1794810`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/mythofempiresserver/](../server-templates/mythofempiresserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
