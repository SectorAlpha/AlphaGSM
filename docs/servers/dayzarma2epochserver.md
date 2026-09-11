# DayZ Arma 2 Epoch

This guide covers the `dayzarma2epochserver` module in AlphaGSM.

## Status

`dayzarma2epochserver` is currently `ENABLED (AUTH)`.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Arma 2: Combined Operations dedicated server app `33935`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayzarma create dayzarma2epochserver
```

Run setup:

```bash
alphagsm mydayzarma setup
```

Start it:

```bash
alphagsm mydayzarma start
```

Check it:

```bash
alphagsm mydayzarma status
```

Stop it:

```bash
alphagsm mydayzarma stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayzarma update
alphagsm mydayzarma backup
```

## Notes

- Module name: `dayzarma2epochserver`
- Default port: 2302

<!-- alphagsm-server-variables:start -->

## Server variables

After `create dayzarma2epochserver`, inspect or change these with `set`:

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

- **Executable**: `arma2oaserver`
- **Location**: `<install_dir>/arma2oaserver`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `33935`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/dayzarma2epochserver/](../server-templates/dayzarma2epochserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
