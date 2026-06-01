# StarRupture

This guide covers the `starruptureserver` module in AlphaGSM.

Status: supported on Linux through the shared Docker `wine-proton` runtime.

## Requirements

- `docker`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarrupt create starruptureserver
```

Run setup:

```bash
alphagsm mystarrupt setup
```

Start it:

```bash
alphagsm mystarrupt start
```

Check it:

```bash
alphagsm mystarrupt status
```

Stop it:

```bash
alphagsm mystarrupt stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the Windows dedicated server payload for app `3809400`
- AlphaGSM stages `DSSettings.txt` into the install root before launch

## Useful Commands

```bash
alphagsm mystarrupt update
alphagsm mystarrupt backup
```

## Notes

- Module name: `starruptureserver`
- Default port: 7777
- Health surface: generic `udp` on the managed main game port

## Developer Notes

### Run File

- **Executable**: `StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe`
- **Location**: `<install_dir>/StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe`
- **Runtime**: shared Docker `wine-proton`
- **SteamCMD App ID**: `3809400`

### Server Configuration

- **Config file**: `<install_dir>/DSSettings.txt`
- **Template**: [server-templates/starruptureserver/DSSettings.txt](../server-templates/starruptureserver/DSSettings.txt)
- **Managed fields**: AlphaGSM refreshes `SessionName` from the configured server name before each start

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
