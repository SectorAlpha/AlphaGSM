# Killing Floor 2

This guide covers the `kf2server` module in AlphaGSM.

`kf2server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykf2serve create kf2server
```

Run setup:

```bash
alphagsm mykf2serve setup
```

Start it:

```bash
alphagsm mykf2serve start
```

Check it:

```bash
alphagsm mykf2serve status
```

Stop it:

```bash
alphagsm mykf2serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mykf2serve update
alphagsm mykf2serve backup
```

## Notes

- Module name: `kf2server`
- Default port: 7777
- Default Steam query port: 27015
- `query` and `info` use the configured A2S query port. Docker publishes this
  UDP listener separately from the gameplay port.

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Location**: `<install_dir>/Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232130`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/kf2server/](../server-templates/kf2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
