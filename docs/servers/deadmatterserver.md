# Dead Matter

This guide covers the `deadmatterserver` module in AlphaGSM.

## Status

`deadmatterserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Dead Matter dedicated server app `1110990`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydeadmatt create deadmatterserver
```

Run setup:

```bash
alphagsm mydeadmatt setup
```

Start it:

```bash
alphagsm mydeadmatt start
```

Check it:

```bash
alphagsm mydeadmatt status
```

Stop it:

```bash
alphagsm mydeadmatt stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydeadmatt update
alphagsm mydeadmatt backup
```

## Notes

- Module name: `deadmatterserver`
- Default port: 27016

<!-- alphagsm-server-variables:start -->

## Server variables

After `create deadmatterserver`, inspect or change these with `set`:

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

- **Executable**: `DeadMatterServer.sh`
- **Location**: `<install_dir>/DeadMatterServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1110990`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/deadmatterserver/](../server-templates/deadmatterserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
