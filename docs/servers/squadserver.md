# Squad

This guide covers the `squadserver` module in AlphaGSM.

`squadserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline.
The anonymous Workshop lifecycle passed in both process and Docker runtimes on
2026-10-15 in [CI run 38748333313](https://github.com/SectorAlpha/AlphaGSM/actions/runs/38748333313).
Local runs use the process runtime unless you select Docker.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquadser create squadserver
```

Run setup:

```bash
alphagsm mysquadser setup
```

Start it:

```bash
alphagsm mysquadser start
```

Check it:

```bash
alphagsm mysquadser status
```

Stop it:

```bash
alphagsm mysquadser stop
```

## Setup Details

Setup configures:

- the game port (default 7787)
- the Steam query port (default game port + 1)
- the RCON port (default game port + 2) and beacon port (default game port + 10)
- a generated local RCON password, saved privately in AlphaGSM's server state
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquadser update
alphagsm mysquadser backup
```

## Notes

- Module name: `squadserver`
- Default game port: 7787
- Modern Squad uses EOS for its server browser. AlphaGSM `query` and `info`
  use native RCON `ShowServerInfo` and `ShowCurrentMap` to report actual game
  health. Setup syncs `IP`, `Port`, and `Password` in
  `SquadGame/ServerConfig/Rcon.cfg`; unrelated options remain intact.
- `set rconport`, `set beaconport`, and `set adminpassword` support local server
  administration. This password is generated locally and requires no Steam or
  EOS account credentials. Keep the RCON port accessible only to trusted hosts.

<!-- alphagsm-server-variables:start -->

## Server variables

After `create squadserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

`adminpassword` is a secret schema-backed setting for local RCON administration.
`set --list` redacts its value. The native RCON file is restricted to its owner.
Use the live command list for ports and other supported settings.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `SquadGameServer.sh`
- **Location**: `<install_dir>/SquadGameServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `403240`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/squadserver/](../server-templates/squadserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: anonymous native Unreal plugin staging and engine loading
  verified in process and Docker runtimes.

## Workshop plugins and maps

```bash
alphagsm myserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=3516838562
alphagsm myserver mod add workshop-collection COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

AlphaGSM validates Workshop items against Squad's game AppID `393380`
and downloads without Steam credentials. A complete Linux cooked content plugin,
its `.uplugin` descriptor and matching `.mi` Workshop identity are required.
PAK and IOStore files are staged under `SquadGame/Plugins/Mods/<item-id>/`;
Windows and macOS cooked assets are omitted.

The engine discovers these plugins at startup. Select the appropriate mod layer
using the game's normal layer rotation or admin commands. A downloaded plugin
does not establish that the current server build can load its SDK version.

The process and Docker integrations used ModLoader `3516838562`, verified its native PAK and
IOStore mounts, successful serialization and registered game layer, then checked
`query` and `info` through native RCON. Cleanup followed by a fresh restart found
zero mod descriptors and no ModLoader mount. The earlier process validation used
the existing one-minute timeout and kill fallback; graceful saving remains
unverified.

`mod remove workshop ID_OR_URL` followed by `mod apply` removes selected owned
files. `mod cleanup` clears the desired list and removes unchanged files owned
by AlphaGSM. Operator plugins and files remain present. Edited owned files block
replacement or cleanup instead of being overwritten.
