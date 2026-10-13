# Left 4 Dead 2

This guide covers the `l4d2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Support Status

`l4d2server` is fully supported. AlphaGSM now installs app `222860`
anonymously by staging the Windows depots first and then applying the Linux
depots into the same server tree, which matches the current working SteamCMD
install path for Left 4 Dead 2 Dedicated Server.

## Quick Start

Create the server:

```bash
alphagsm myl4d2serv create l4d2server
```

Run setup:

```bash
alphagsm myl4d2serv setup
```

Start it:

```bash
alphagsm myl4d2serv start
```

Check it:

```bash
alphagsm myl4d2serv status
```

Stop it:

```bash
alphagsm myl4d2serv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

`setup` now uses the proven two-phase anonymous SteamCMD install flow for app
`222860`: Windows depots first, then Linux depots in the same directory. This
works around the current SteamCMD `Invalid platform` failure for a Linux-only
anonymous install.

## Useful Commands

```bash
alphagsm myl4d2serv update
alphagsm myl4d2serv backup
```

## Notes

- Module name: `l4d2server`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create l4d2server`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `c5m1_waterfront`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `8`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Left 4 Dead 2`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `222860`

### Server Configuration

- **Config file**: `left4dead2/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `c5m1_waterfront`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/l4d2server/](../server-templates/l4d2server/)

### Maps and Mods

- **Map directory**: `left4dead2/maps/`
- **Mod directory**: `left4dead2/addons/`
- **Workshop support**: Anonymous item and collection downloads with game AppID
  validation and one bare VPK per item. Live collection load validation is
  pending: Steam's public APIs returned result `9` (unavailable) for collection
  `3819008159` on 2026-10-13.
- **Mod notes**: AlphaGSM manages addons from checked-in `manifest` entries,
  direct `url` entries, GameBanana IDs, Mod DB URLs, and game-validated Workshop
  IDs/collections. The manifest includes MetaMod and SourceMod. Direct URLs
  accept `.vpk` files or supported archives; GameBanana, Mod DB, and manifest
  sources install supported archives. Workshop items must contain one bare
  `.vpk`. `mod cleanup` removes AlphaGSM-tracked files and keeps its local
  cache/state under `.alphagsm/mods/left4dead2/`.
- **Current status**: Fully supported. The current anonymous SteamCMD lane for
  app `222860` works when AlphaGSM stages the Windows depots first and then the
  Linux depots into the same install tree.
- **Map install**: Copy `.bsp` files into `left4dead2/maps/` and add to `left4dead2/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `left4dead2/addons/`.

Examples:

```bash
alphagsm myl4d2 mod add manifest metamod
alphagsm myl4d2 mod add manifest sourcemod
alphagsm myl4d2 mod add url https://mods.example.invalid/custom-campaign.vpk
alphagsm myl4d2 mod add gamebanana 12345
alphagsm myl4d2 mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
alphagsm myl4d2 mod add workshop ITEM_ID
alphagsm myl4d2 mod add workshop-collection COLLECTION_ID
alphagsm myl4d2 mod add workshop "https://steamcommunity.com/sharedfiles/filedetails/?id=762591677"
alphagsm myl4d2 mod apply
alphagsm myl4d2 mod cleanup
```

Workshop items use the game AppID `550`, rather than server-tool AppID
`222860`. Both item and collection commands accept IDs or Steam Workshop URLs.
AlphaGSM checks the collection and every nested item against `550`
before saving additions. Workshop VPKs install as
`left4dead2/addons/workshop/<item-id>.vpk`; enabled desired addons auto-apply
before launch. Re-importing a collection adds new items without deleting old
ones. Remove an individual entry with `mod remove workshop ITEM_ID`, then
`mod apply`. Steam can still require an entitled account for some downloads.

To test the supplied collection on process and Docker runtimes:

```bash
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_L4D2_WORKSHOP=1 ALPHAGSM_WORK_DIR=/tmp/alphagsm-work \
PYTHONPATH=.:src python3 -m pytest tests/integration_tests/test_l4d2server.py \
  -k workshop_collection -s
```

The test defaults to collection `3819008159`; set
`ALPHAGSM_L4D2_WORKSHOP_COLLECTION` to override it. It exercises AlphaGSM
create/setup/start/readiness/status/query/info/stop and requires every addon
in the running engine's mounted search paths. File existence alone cannot
pass. This proves VPK mounting, rather than client rendering or every gameplay
effect. An unavailable collection fails before downloading the server.

The streamed equivalent is
`ALPHAGSM_RUN_L4D2_WORKSHOP=1 make smoke-test SMOKE_TEST=run_l4d2server.sh`.
The normal lifecycle test and smoke runner do not require an external Workshop
collection unless this option is enabled.
