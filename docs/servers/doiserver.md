# Day of Infamy

This guide covers the `doiserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydoiserve create doiserver
```

Run setup:

```bash
alphagsm mydoiserve setup
```

Start it:

```bash
alphagsm mydoiserve start
```

Check it:

```bash
alphagsm mydoiserve status
```

Stop it:

```bash
alphagsm mydoiserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm mydoiserve update
alphagsm mydoiserve backup
```

## Notes

- Module name: `doiserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `462310`

### Server Configuration

- **Config file**: `doi/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `bastogne stronghold`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/doiserver/](../server-templates/doiserver/)

### Maps and Mods

- **Map directory**: `doi/maps/`
- **Mod directory**: `doi/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/doi/`.
- **Map install**: Copy `.bsp` files into `doi/maps/` and add to `doi/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `doi/addons/`.
