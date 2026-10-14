# Squad 44

This guide covers the `squad44server` module in AlphaGSM.

`squad44server` passed stock process and Docker integration plus Docker smoke
on Ubuntu 24.04 in CI run `38537399526` on 2026-10-14. Both runtimes load a
native world and answer real A2S query, info and JSON requests; shutdown is
verified. Docker smoke reported `Veghel Offensive Random 01` with 0/80 players.

AlphaGSM prefers the Steam SDK supplied with the dedicated server. Stop currently
uses the existing forced-stop fallback; graceful saving is not established.
Native Workshop loading remains pending separate validation.

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

- the game port (default 7787)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquad44s update
alphagsm mysquad44s backup
```

## Notes

- Module name: `squad44server`
- Default game port: 7787; default managed query port: game port plus one

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
alphagsm myserver mod add workshop CURRENT_LINUX_WORKSHOP_ID_OR_URL
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

CI smoke and integration runs now require Workshop content. The previous
SquidBots fixture (`2909251852`) was rejected by the engine: its `.mi` declares
`Engine=4.27.2`, while current SDK fixtures use `4.27.2.SQ44`. The default fixture
is Ramelle (`2387944294`), whose author advertises Linux support. The test derives
its plugin name from staged metadata and requires the matching Workshop ID and
current SDK identity before engine checks. Anonymous access and process/Docker
native-load proof for this replacement fixture are still pending.

For an explicitly requested local run, set `ALPHAGSM_RUN_SQUAD44_WORKSHOP=1`.
Override `ALPHAGSM_SQUAD44_WORKSHOP_ID` (ID or URL) and optionally
`ALPHAGSM_SQUAD44_WORKSHOP_PLUGIN` (exact staged plugin name). A different item
also requires `ALPHAGSM_SQUAD44_WORKSHOP_LAYER` with its documented native layer.
The default test selects `Ramelle_Offensive_01` as the sole entry in the disposable
server's `MapRotation.cfg`. Native PAK precacher records and the engine's exact
successful mod-mount/serialization message are checked across
the managed runtime output and the engine log: early startup output can precede
the opening of the engine log file. The test also requires fresh native world
construction and completed `LoadMap` evidence for that layer, plus
the same layer reported by real A2S metadata. Startup and query timeouts remain
failures. CI enables this check automatically; replacement-fixture results remain
pending.
