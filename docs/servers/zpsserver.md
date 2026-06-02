# Zombie Panic! Dedicated Server

This guide covers the `zpsserver` module in AlphaGSM.

## Requirements

- `docker`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myzpsserve create zpsserver
```

Run setup:

```bash
alphagsm myzpsserve setup
```

Start it:

```bash
alphagsm myzpsserve start
```

Check it:

```bash
alphagsm myzpsserve status
```

Stop it:

```bash
alphagsm myzpsserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the dedicated server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myzpsserve update
alphagsm myzpsserve backup
```

## Notes

- Module name: `zpsserver`
- Default port: `27015`
- Current status: disabled in automated testing. SteamCMD app `4523420` now stages the current GoldSrc dedicated payload and Docker launches `hlds_run`, but HLDS still dies at `SteamAPI_Init() failed; create pipe failed` after loading `/root/.steam/sdk32/steamclient.so`, before A2S readiness.

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc
- **SteamCMD App ID**: `4523420`

### Server Configuration

- **Config file**: `zp/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `zph_industry`
- **Max players**: `20`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: No checked-in template; the staged payload ships `zp/server.cfg`

### Maps and Mods

- **Map directory**: `zp/maps/`
- **Mod directory**: `zp/`
- **Workshop support**: No
- **Mod notes**: The old Source-era addon assumptions no longer match the current dedicated app. The live 2026 payload is a GoldSrc `zp/` server tree.
- **Map install**: Copy `.bsp` files into `zp/maps/` and add them to `zp/mapcycle.txt`.
