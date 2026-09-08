# Icarus

This guide covers the `icarusserver` module in AlphaGSM.

`icarusserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myicarusse create icarusserver
```

Run setup:

```bash
alphagsm myicarusse setup
```

Start it:

```bash
alphagsm myicarusse start
```

Check it:

```bash
alphagsm myicarusse status
```

Stop it:

```bash
alphagsm myicarusse stop
```

## Setup Details

Setup configures:

- the game port (default 17778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myicarusse update
alphagsm myicarusse backup
```

## Notes

- Module name: `icarusserver`
- Default port: 17778
- Query/info uses native Steam A2S on `queryport` in both process and Docker
  runtimes. The earlier TCP-only check did not establish game readiness.

## Developer Notes

### Run File

- **Executable**: `IcarusServer.exe`
- **Location**: `<install_dir>/IcarusServer.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2089300`

The Linux Docker path uses the shared `wine-proton` runtime image and its
Xvfb/software-GL support. Anonymous SteamCMD installs app `2089300`.
Readiness requires the server to answer A2S on the configured query port.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/icarusserver/](../server-templates/icarusserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
