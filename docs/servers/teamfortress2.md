# Team Fortress 2-specific

This guide covers the `teamfortress2` module in AlphaGSM.

The checked-in support tracker currently marks the canonical Team Fortress 2
surface as `PASSED` on the documented Ubuntu 24.04 Linux baseline under the
`tf2` module id. `teamfortress2` is the package-backed canonical import
surface behind that validated TF2 server path.

## Requirements

The current AlphaGSM process integration requires Linux because it uses
`srcds_run` and Linux Steam client libraries. Setup rejects incompatible hosts
before downloading. Docker requires a Linux-container daemon, including when
Docker runs on a Windows desktop. Installation still uses the Linux SteamCMD
client on the manager host; run AlphaGSM itself in Linux or in the manager
container for this setup path.

- Optional `screen` or `tmux`; the subprocess backend is also available
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- For source installations, Python packages from `requirements-runtime.txt`

## Quick Start

Create the server:

```bash
alphagsm myteamfort create teamfortress2
```

Run setup:

```bash
alphagsm myteamfort setup
```

Start it:

```bash
alphagsm myteamfort start
```

Check it:

```bash
alphagsm myteamfort status
```

Stop it:

```bash
alphagsm myteamfort stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

The native TF2 config lives at `tf/cfg/server.cfg`. AlphaGSM keeps the
following values in sync through `set`:

- `set gamemap` aliases `map`, `startmap`, and `level`
- `set servername` updates the `hostname` entry in `server.cfg`
- `set rconpassword` updates `rcon_password`
- `set serverpassword` updates `sv_password`

Examples:

```bash
alphagsm myteamfort set gamemap --describe
alphagsm myteamfort set gamemap cp_dustbowl
alphagsm myteamfort set rconpassword secret
```

## Useful Commands

```bash
alphagsm myteamfort update
alphagsm myteamfort update -r
alphagsm myteamfort backup
```

`-r` restarts after the SteamCMD update. `-v` validates the files. See
[Updating Servers And AlphaGSM](../updating.md).

## Installing Mods

The supported path is AlphaGSM's checked-in `manifest` list. Add what you want,
then apply it. The full operator guide is
[Installing Mods](../installing-mods.md).

```bash
alphagsm myteamfort mod add manifest metamod
alphagsm myteamfort mod add manifest sourcemod
alphagsm myteamfort mod apply
alphagsm myteamfort mod list
```

`sourcemod` can be pinned to a registry channel such as `1.12`. `curated` is
still accepted as an alias for `manifest`. Files land under `tf/addons/` and
`tf/cfg/`. `mod cleanup` removes only AlphaGSM-owned addon files.

GameBanana and Mod DB ids/URLs are also accepted. Workshop maps use the engine's
native loader described below.

`mod add workshop-collection COLLECTION_ID` also imports a collection snapshot.
Both item and collection identifiers accept Steam Community Workshop URLs.
Steam metadata must identify every item and nested collection as TF2 (AppID
`440`) before AlphaGSM saves additions.

## Notes

- Module name: `teamfortress2`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create teamfortress2`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `dir` | — | string | Install directory for the server. |
| `exe_name` | — | string | Server executable filename. |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `cp_dustbowl`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM TF2 Server`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232250`

### Server Configuration

- **Config files**: `server.cfg`
- **Template**: See [server-templates/teamfortress2/](../server-templates/teamfortress2/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Curated mod directories**: `tf/addons` and `tf/cfg`
- **Curated mod examples**: `sourcemod`, `metamod`
- **Workshop support**: Native multiplayer maps with verified anonymous process activation.


## Native Workshop multiplayer maps

```bash
alphagsm mytf2 mod add workshop 454299390
alphagsm mytf2 mod add workshop-collection YOUR_COLLECTION_ID
alphagsm mytf2 mod apply
alphagsm mytf2 set map workshop/454299390
alphagsm mytf2 start
```

Official Steam Community item/collection URLs also work. AlphaGSM validates AppID
`440` and map-mode metadata, then configures the engine's native
`tf_workshop_map_sync` commands in `tf/cfg/alphagsm_workshop.cfg`. Cosmetic uploads
are rejected. Native Workshop map names are `workshop/ITEM_ID`; the engine resolves
the full map name and downloads the current map itself. No Steam account token
or Workshop API key is supplied. The existing curated map and addon commands stay
available. See [Valve's native map-loader update](https://www.teamfortress.com/post.php?id=17214).
AlphaGSM supplies an absolute `-ugcpath` under the install's `steamapps/workshop`
directory while native Workshop maps are enabled. Docker uses the mounted
container path and the host user's identity, with a private writable HOME and
Steam library metadata, so the native downloader sees the same initialized
library layout as a process server.

Apply while stopped. AlphaGSM refuses a preexisting unowned sync configuration
and externally edited managed files. `mod cleanup` removes only its unchanged
sync configuration; engine-managed Workshop caches and the operator's selected
map setting remain. Choose an ordinary installed map before restarting after
cleanup if you want to stop playing the Workshop map.

The public [cp_orange_x3 fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=454299390)
was verified as AppID `440` on 2026-10-13. The complete process lifecycle passed on 2026-10-13 with real A2S and fresh native
mount evidence. The normal stop-timeout fallback was used before shutdown
verification; owned configuration cleanup also passed.
Its opt-in check requires actual custom-map A2S responses together with a fresh
`tf_workshop_map_status` row marking the exact item and canonical `.ugcITEM_ID`
map ready, and a fresh console `status` showing that same canonical map running.
A pending `workshop/ITEM_ID` advertisement cannot satisfy it. TF2 resolves its
Workshop BSP through Steam's native item-install API rather than requiring the
item directory in the engine's search paths. The check also requires full CLI
shutdown and configuration cleanup.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_TF2_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_tf2.py -k workshop

ALPHAGSM_WORK_DIR=/path/on/large/disk TF2_WORKSHOP_ITEM=454299390 \
make smoke-test SMOKE_TEST=run_tf2.sh
```

A collection override uses `ALPHAGSM_TF2_WORKSHOP_COLLECTION`; select its test map
with `ALPHAGSM_TF2_WORKSHOP_LOAD_ITEM` and `ALPHAGSM_TF2_WORKSHOP_MAP`. Smoke accepts
`TF2_WORKSHOP_COLLECTION`, `TF2_WORKSHOP_LOAD_ITEM`, and `TF2_WORKSHOP_MAP`.
Docker validation remains pending an SSD-backed Docker endpoint.
