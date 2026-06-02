# Subsistence

This guide covers the `subsistenceserver` module in AlphaGSM.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysubsiste create subsistenceserver
```

Run setup:

```bash
alphagsm mysubsiste setup
```

Start it:

```bash
alphagsm mysubsiste start
```

Check it:

```bash
alphagsm mysubsiste status
```

Stop it:

```bash
alphagsm mysubsiste stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the A2S query port (default 27016)
- the max players value (default 10)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm mysubsiste update
alphagsm mysubsiste backup
```

## Notes

- Module name: `subsistenceserver`
- Default game port: `27015`
- Default query port: `27016`

## Developer Notes

### Run File

- **Executable**: `Binaries/Win32/Subsistence.exe`
- **Location**: `<install_dir>/Binaries/Win32/Subsistence.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `1362640`

Current validation status: fresh 2026-06-02 Docker `wine-proton` repros proved
that app `1362640` still is not enablement-ready on Linux. The full anonymous
SteamCMD payload now reaches both shipped Windows launchers, but neither one
gets to A2S readiness:

- `Binaries/Win64/Subsistence.exe` and `Binaries/Win64/UDK.exe` both exit
  immediately with `Please install DirectX 9.0c or later`
- staging `d3dx9` into a server-local Wine prefix does not clear that Win64
  prerequisite gate
- the older `Binaries/Win32/Subsistence.exe` path now fails at the same
  DirectX prerequisite gate before readiness

So the current blocker is no longer a vague Proton crash; it is a repeatable
UE3 Windows prerequisite failure on the validated Linux Docker lane.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `10`
- **Template**: See [server-templates/subsistenceserver/](../server-templates/subsistenceserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
