# Chivalry: Medieval Warfare

This guide covers the `chivalryserver` module in AlphaGSM.

## Status

`chivalryserver` is currently `ENABLED (AUTH)`.

Before `setup` or `start`, authenticate Steam or SteamCMD with an account
entitled to Chivalry: Medieval Warfare Dedicated Server app `220070`.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mychivalry create chivalryserver
```

Run setup:

```bash
alphagsm mychivalry setup
```

Start it:

```bash
alphagsm mychivalry start
```

Check it:

```bash
alphagsm mychivalry status
```

Stop it:

```bash
alphagsm mychivalry stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mychivalry update
alphagsm mychivalry backup
```

## Notes

- Module name: `chivalryserver`
- Default port: 7777
- Default query port: 27015
- Current validation status: AlphaGSM now repairs the missing `PhysXUpdateLoader.so` alias, launches from the correct Linux working directory, syncs the managed `Port`/`PeerPort`/`QueryPort` values into `PCServer-UDKEngine.ini`, and exposes the install-root Steam library paths so the Linux binary can locate the shipped `steamclient.so`, but anonymous Linux startup still aborts in `SteamAPI_Init()` / `SteamAPI_IsSteamRunning()` before any working A2S `query`/`info` path appears.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create chivalryserver`, inspect or change these with `set`:

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

- **Executable**: `Binaries/Linux/UDKGameServer-Linux`
- **Location**: `<install_dir>/Binaries/Linux/UDKGameServer-Linux`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `220070`

AlphaGSM now launches Chivalry with the configured game port embedded in the
UDK URL, for example `AOCTO-Battlegrounds_V3_P?Port=7777?QueryPort=27015?steamsockets`, so
the runtime actually binds the game port selected during `setup` and exposes A2S
on the configured query port.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/chivalryserver/](../server-templates/chivalryserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
