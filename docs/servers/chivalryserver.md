# Chivalry: Medieval Warfare

This guide covers the `chivalryserver` module in AlphaGSM.

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
