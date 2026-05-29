# Eco

This guide covers the `ecoserver` module in AlphaGSM.

Status: PASSED on 2026-05-29 via the shared `steamcmd-linux` Docker runtime.

## Requirements

- `screen`
- `docker` for the validated Linux runtime path
- For local process launches on Linux, install `libgdiplus` plus the usual SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myecoserve create ecoserver
```

Run setup:

```bash
alphagsm myecoserve setup
```

Start it:

```bash
alphagsm myecoserve start
```

Check it:

```bash
alphagsm myecoserve status
```

Stop it:

```bash
alphagsm myecoserve stop
```

## Setup Details

Setup configures:

- the game port (default 3000)
- the install directory
- SteamCMD downloads the server files
- AlphaGSM writes `Configs/Network.eco` so the managed main port stays in sync with Eco's derived web, RCON, and Steam side ports

## Useful Commands

```bash
alphagsm myecoserve update
alphagsm myecoserve backup
```

## Notes

- Module name: `ecoserver`
- Default port: 3000
- AlphaGSM launches Eco in `-offline` mode for anonymous SteamCMD installs
- `query`, `info`, and `info --json` use Eco's live generic `tcp` surface on the managed main port
- The current validated stop path may fall back to AlphaGSM's built-in forced kill after the normal grace period if Eco ignores the generic console shutdown command

## Developer Notes

### Run File

- **Executable**: `EcoServer`
- **Location**: `<install_dir>/EcoServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `739590`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/ecoserver/](../server-templates/ecoserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
