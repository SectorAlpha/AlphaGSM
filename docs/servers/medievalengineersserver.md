# Medieval Engineers

This guide covers the `medievalengineersserver` module in AlphaGSM.

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- Proton compatibility runtime on Linux; bare Wine is not sufficient for the current dedicated server build

## Quick Start

Create the server:

```bash
alphagsm mymedieval create medievalengineersserver
```

Run setup:

```bash
alphagsm mymedieval setup
```

Start it:

```bash
alphagsm mymedieval start
```

Check it:

```bash
alphagsm mymedieval status
```

Stop it:

```bash
alphagsm mymedieval stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymedieval update
alphagsm mymedieval backup
```

## Notes

- Module name: `medievalengineersserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DedicatedServer64/MedievalEngineersDedicated.exe`
- **Location**: `<install_dir>/DedicatedServer64/MedievalEngineersDedicated.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `367970`

### Server Configuration

- **Config files**: `global.cfg`
- **Template**: See [server-templates/medievalengineersserver/](../server-templates/medievalengineersserver/) if available
- **Current status**: Disabled in CI. Fresh Docker `wine-proton` validation now proves the remaining blocker is inside the Windows runtime bootstrap, not SteamCMD or a missing executable: anonymous app `367970` installs the full dedicated payload, but under Proton the dedicated EXE throws `System.PlatformNotSupportedException: Video driver  not supported`, then emits follow-on missing-resource and XML-serializer exceptions including missing `Content\\Textures\\Splashscreens` before AlphaGSM can reach server logs or A2S readiness.

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
