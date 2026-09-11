# Reign Of Kings

This guide covers the `reignofkingsserver` module in AlphaGSM.

## Status

`reignofkingsserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Reign of Kings dedicated server app `381690`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreignofk create reignofkingsserver
```

Run setup:

```bash
alphagsm myreignofk setup
```

Start it:

```bash
alphagsm myreignofk start
```

Check it:

```bash
alphagsm myreignofk status
```

Stop it:

```bash
alphagsm myreignofk stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreignofk update
alphagsm myreignofk backup
```

## Notes

- Module name: `reignofkingsserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create reignofkingsserver`, inspect or change these with `set`:

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

- **Executable**: `Server.exe`
- **Location**: `<install_dir>/Server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `381690`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `40`
- **Template**: See [server-templates/reignofkingsserver/](../server-templates/reignofkingsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
