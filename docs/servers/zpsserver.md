# Zombie Panic! Dedicated Server

This guide covers the `zpsserver` module in AlphaGSM.

`zpsserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection around that provider-managed authentication prerequisite, while local runs remain process-backed by default unless you opt into the Docker backend.

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
- Current status: `ENABLED (AUTH)`. SteamCMD app `4523420` stages the current GoldSrc dedicated payload, and the dedicated launch contract now matches SteamDB (`hlds_run -game zp -steam -secure`), but the validated Linux lane still expects a real authenticated Steam client session. Fresh Docker probes still stop at `SteamAPI_IsSteamRunning() did not locate a running instance of Steam` / `SteamAPI_Init() failed; create pipe failed` before A2S readiness.

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
