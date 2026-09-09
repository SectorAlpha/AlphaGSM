# Battle Cry of Freedom

This guide covers the `battlecryoffreedomserver` module in AlphaGSM.

`battlecryoffreedomserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Wine or Proton-GE on Linux
- `xvfb-run` on Linux process runtimes
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybattlecr create battlecryoffreedomserver
```

Run setup:

```bash
alphagsm mybattlecr setup
```

Start it:

```bash
alphagsm mybattlecr start
```

Check it:

```bash
alphagsm mybattlecr status
```

Stop it:

```bash
alphagsm mybattlecr stop
```

## Setup Details

Setup configures:

- the game port (default 8262)
- the configured query port (default 8263)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybattlecr update
alphagsm mybattlecr backup
```

## Notes

- Linux process launches require `xvfb-run` during Wine initialization; the
  shared Wine/Proton Docker image supplies the matching virtual display.
  Native port configuration still needs verification against the shipped
  `ServerConfiguration.ini` and launcher.
- Module name: `battlecryoffreedomserver`
- Default game port: 8262
- Default query port: 8263
- `query`, `info`, and `info --json` use the validated TCP health surface on
  the managed game port.

## Developer Notes

### Run File

- **Executable**: `BCoF.exe`
- **Location**: `<install_dir>/BCoF.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1362540`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/battlecryoffreedomserver/](../server-templates/battlecryoffreedomserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
