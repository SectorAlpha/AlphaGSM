# BROKE PROTOCOL

This guide covers the `brokeprotocolserver` module in AlphaGSM.

## Status

`brokeprotocolserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
BROKE PROTOCOL app `696370`. The current dedicated-server hosting flow relies
on the main game install tree rather than a separate anonymous Linux server
tool.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybrokepro create brokeprotocolserver
```

Run setup:

```bash
alphagsm mybrokepro setup
```

Start it:

```bash
alphagsm mybrokepro start
```

Check it:

```bash
alphagsm mybrokepro status
```

Stop it:

```bash
alphagsm mybrokepro stop
```

## Setup Details

Setup configures:

- the game port (default 27777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybrokepro update
alphagsm mybrokepro backup
```

## Notes

- Module name: `brokeprotocolserver`
- Default port: 27777

<!-- alphagsm-server-variables:start -->

## Server variables

After `create brokeprotocolserver`, inspect or change these with `set`:

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

- **Executable**: `Start.sh`
- **Location**: `<install_dir>/Start.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `696370`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/brokeprotocolserver/](../server-templates/brokeprotocolserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
