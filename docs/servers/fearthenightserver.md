# Fear the Night

This guide covers the `fearthenightserver` module in AlphaGSM.

`fearthenightserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. GitHub validation uses the supported Docker `wine-proton`
runtime, with generic `udp` `query` / `info` on the managed game port
instead of A2S on `queryport`.

## Requirements

- `screen`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfearthen create fearthenightserver
```

Run setup:

```bash
alphagsm myfearthen setup
```

Start it:

```bash
alphagsm myfearthen start
```

Check it:

```bash
alphagsm myfearthen status
```

Stop it:

```bash
alphagsm myfearthen stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the dedicated query port (default 27015, still not the live Linux query surface)
- the session name and max player count
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myfearthen update
alphagsm myfearthen backup
```

## Notes

- Module name: `fearthenightserver`
- Default game port: `7777/udp`
- Default stored query port: `27015/udp`
- Current CI status: passed on 2026-05-29. Fresh smoke and focused integration now pass on the Linux/Proton process-backed path.
- AlphaGSM `query`, `info`, and `info --json` currently use generic `udp` reachability on the managed game port for Linux/Wine-Proton runs because the dedicated server still does not expose a working A2S listener on the configured `queryport`.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create fearthenightserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Moonlight/Binaries/Win64/MoonlightServer.exe`
- **Location**: `<install_dir>/Moonlight/Binaries/Win64/MoonlightServer.exe`
- **Engine**: UE4-based Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `764940`
- **Validated Linux launch contract**: `MoonlightServer.exe Pittsburgh_Overworld?listen?Port=<port>?QueryPort=<queryport>?SessionName=<name>?MaxPlayers=<maxplayers> -game -server -log`

### Server Configuration

- **Managed config files**:
  - `Moonlight/Saved/Config/WindowsServer/Engine.ini`
  - `Moonlight/Saved/Config/WindowsServer/GameUserSettings.ini`
- **Managed keys**: `port`, `queryport`, `maxplayers`, `servername`, `startmap`
- **Template**: See [server-templates/fearthenightserver/](../server-templates/fearthenightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
