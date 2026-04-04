# Stationeers

This guide covers the `stationeersserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- A host/runtime that can start the Unity dedicated server cleanly in headless mode

## Quick Start

Create the server:

```bash
alphagsm mystatione create stationeersserver
```

Run setup:

```bash
alphagsm mystatione setup
```

Start it:

```bash
alphagsm mystatione start
```

Check it:

```bash
alphagsm mystatione status
```

Stop it:

```bash
alphagsm mystatione stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystatione update
alphagsm mystatione backup
```

## Notes

- Module name: `stationeersserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `rocketstation_DedicatedServer.x86_64`
- **Location**: `<install_dir>/rocketstation_DedicatedServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `600760`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `10`
- **Template**: See [server-templates/stationeersserver/](../server-templates/stationeersserver/) if available
- **Current status**: Disabled in CI. The Linux dedicated server starts under Unity `NullGfxDevice`, throws a `SetConsoleOutputCP` startup exception, and never opens its game port in headless CI.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
