# Dystopia

This guide covers the `dysserver` module in AlphaGSM.

## Requirements

- authenticated Steam or SteamCMD access to the Dystopia Beta Dedicated Server tool (`app 17595`)
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydysserve create dysserver
```

Run setup:

```bash
alphagsm mydysserve setup
```

Start it:

```bash
alphagsm mydysserve start
```

Check it:

```bash
alphagsm mydysserve status
```

Stop it:

```bash
alphagsm mydysserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the auth-gated beta dedicated server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm mydysserve update
alphagsm mydysserve backup
```

## Notes

- Module name: `dysserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run.sh`
- **Location**: `<install_dir>/srcds_run.sh`
- **Engine**: Source
- **SteamCMD App ID**: `17595`

Current support status: `ENABLED (AUTH)`. The historical Dystopia Linux server
guide points to the `Previous` beta lane, and fresh 2026-06-02 SteamCMD probes
show that this supported beta-dedicated path now maps to app `17595`, which
returns `No subscription` on anonymous SteamCMD. AlphaGSM therefore treats
`dysserver` as an auth-backed supported server instead of a generic runtime
failure.

If you only use the older anonymous app `17585` path, AlphaGSM can still stage
full content, but current Docker-backed Source repros show the legacy 32-bit
server binary exiting immediately before A2S readiness. The supported route is
to authenticate Steam or SteamCMD for app `17595`.

### Server Configuration

- **Config file**: `dystopia/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dys_broadcast`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/dysserver/](../server-templates/dysserver/)

### Maps and Mods

- **Map directory**: `dystopia/maps/`
- **Mod directory**: `dystopia/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/dystopia/`.
- **Map install**: Copy `.bsp` files into `dystopia/maps/` and add to `dystopia/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `dystopia/addons/`.
