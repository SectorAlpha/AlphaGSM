# GROUND BRANCH

This guide covers the `groundbranchserver` module in AlphaGSM.

`groundbranchserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygroundbr create groundbranchserver
```

Run setup:

```bash
alphagsm mygroundbr setup
```

Start it:

```bash
alphagsm mygroundbr start
```

Check it:

```bash
alphagsm mygroundbr status
```

Stop it:

```bash
alphagsm mygroundbr stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mygroundbr update
alphagsm mygroundbr backup
```

## Notes

- AlphaGSM uses the dedicated server's documented `MultiHome=0.0.0.0`, `Port=`,
  `QueryPort=`, and `?MaxPlayers=` options. Both game and Steam query ports use
  UDP. Current SteamSockets builds under Proton do not expose a local A2S reply,
  so `query`, `info`, and readiness checks probe the configured game port.
  See the [developer's server guide](https://steamcommunity.com/sharedfiles/filedetails/?id=1449083065).
- Module name: `groundbranchserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `GroundBranch/Binaries/Win64/GroundBranchServer-Win64-Shipping.exe`
- **Location**: `<install_dir>/GroundBranch/Binaries/Win64/GroundBranchServer-Win64-Shipping.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `476400`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `16`
- **Template**: See [server-templates/groundbranchserver/](../server-templates/groundbranchserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
