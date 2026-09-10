# DUCKSIDE

This guide covers the `ducksideserver` module in AlphaGSM.

## Status

`ducksideserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Duckside dedicated server app `2690320`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myduckside create ducksideserver
```

Run setup:

```bash
alphagsm myduckside setup
```

Start it:

```bash
alphagsm myduckside start
```

Check it:

```bash
alphagsm myduckside status
```

Stop it:

```bash
alphagsm myduckside stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myduckside update
alphagsm myduckside backup
```

## Notes

- Module name: `ducksideserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ducksideserver`, inspect or change these with `set`:

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

- **Executable**: `DucksideServer.exe`
- **Location**: `<install_dir>/DucksideServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2690320`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/ducksideserver/](../server-templates/ducksideserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
