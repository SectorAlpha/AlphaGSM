# Half-Life 2: Deathmatch

This guide covers the `hl2dmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhl2dmser create hl2dmserver
```

Run setup:

```bash
alphagsm myhl2dmser setup
```

Start it:

```bash
alphagsm myhl2dmser start
```

Check it:

```bash
alphagsm myhl2dmser status
```

Stop it:

```bash
alphagsm myhl2dmser stop
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
alphagsm myhl2dmser update
alphagsm myhl2dmser backup
```

## Notes

- Module name: `hl2dmserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `232370`

### Server Configuration

- **Config file**: `hl2mp/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dm_lockdown`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/hl2dmserver/](../server-templates/hl2dmserver/)

### Maps and Mods

- **Map directory**: `hl2mp/maps/`
- **Mod directory**: `hl2mp/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM can now manage Half-Life 2: Deathmatch addons from checked-in `manifest` entries plus direct archive `url` entries, GameBanana ids, and Mod DB page URLs. The local manifest currently includes popular Source admin/plugin stacks such as MetaMod and SourceMod. Archives must unpack into approved addon paths under `hl2mp/addons/`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/hl2dmserver/`.
- **Map install**: Copy `.bsp` files into `hl2mp/maps/` and add to `hl2mp/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `hl2mp/addons/`.

Examples:

```bash
alphagsm myhl2dm mod add manifest metamod
alphagsm myhl2dm mod add manifest sourcemod
alphagsm myhl2dm mod add url https://mods.example.invalid/hl2dm-addon-pack.zip
alphagsm myhl2dm mod add gamebanana 12345
alphagsm myhl2dm mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
alphagsm myhl2dm mod apply
alphagsm myhl2dm mod cleanup
```
