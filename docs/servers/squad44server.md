# Squad 44

This guide covers the `squad44server` module in AlphaGSM.

`squad44server` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The GitHub integration lane exercises process and Docker runtimes. Validation of the Docker host-user change is pending CI; local runs use the process runtime unless you select Docker.

## Requirements

For Docker, run AlphaGSM as a normal user with Docker access. The server rejects root; its container uses your user and group IDs and a private writable home directory.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquad44s create squad44server
```

Run setup:

```bash
alphagsm mysquad44s setup
```

Start it:

```bash
alphagsm mysquad44s start
```

Check it:

```bash
alphagsm mysquad44s status
```

Stop it:

```bash
alphagsm mysquad44s stop
```

## Setup Details

Setup configures:

- the game port (default 27165)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquad44s update
alphagsm mysquad44s backup
```

## Notes

- Module name: `squad44server`
- Default port: 27165

<!-- alphagsm-server-variables:start -->

## Server variables

After `create squad44server`, inspect or change these with `set`:

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

- **Executable**: `PostScriptumServer.sh`
- **Location**: `<install_dir>/PostScriptumServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `746200`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/squad44server/](../server-templates/squad44server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: anonymous native Unreal plugin staging; current engine
  validation in process and Docker is pending.

## Workshop plugins and maps

```bash
alphagsm myserver mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=2909251852
alphagsm myserver mod add workshop-collection COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

AlphaGSM validates Workshop items against Squad 44's game AppID `736220`
and downloads without Steam credentials. A complete Linux cooked content plugin,
its `.uplugin` descriptor and matching `.mi` Workshop identity are required.
PAK and IOStore files are staged under `PostScriptum/Plugins/Mods/<item-id>/`;
Windows and macOS cooked assets are omitted.

The engine discovers these plugins at startup. Select the appropriate mod layer
using the game's normal layer rotation or admin commands. A downloaded plugin
does not establish that the current server build can load its SDK version.

`mod remove workshop ID_OR_URL` followed by `mod apply` removes selected owned
files. `mod cleanup` clears the desired list and removes unchanged files owned
by AlphaGSM. Operator plugins and files remain present. Edited owned files block
replacement or cleanup instead of being overwritten.
