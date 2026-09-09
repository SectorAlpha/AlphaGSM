# Icarus

This guide covers the `icarusserver` module in AlphaGSM.

`icarusserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub validation uses the supported Docker `wine-proton` runtime.
On Linux/Wine, `query` and `info` use the validated generic TCP health
surface on the managed game port.

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
- Query/info uses generic TCP on the managed game port under Linux/Wine.

## Developer Notes

### Run File

- **Executable**: `IcarusServer.exe`
- **Location**: `<install_dir>/IcarusServer.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2089300`

The Linux Docker path uses the shared `wine-proton` runtime image and its
Xvfb/software-GL support. Anonymous SteamCMD installs app `2089300`. Current
Linux/Wine launches open the game port but do not provide a stable A2S reply on
the configured query port, so AlphaGSM reports the live TCP health surface.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/icarusserver/](../server-templates/icarusserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
