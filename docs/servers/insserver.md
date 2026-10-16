# Insurgency

This guide covers the `insserver` module in AlphaGSM.

`insserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinsserve create insserver
```

Run setup:

```bash
alphagsm myinsserve setup
```

Start it:

```bash
alphagsm myinsserve start
```

Check it:

```bash
alphagsm myinsserve status
```

Stop it:

```bash
alphagsm myinsserve stop
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
alphagsm myinsserve update
alphagsm myinsserve backup
```

## Notes

- Module name: `insserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create insserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `embassy_coop checkpoint`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Insurgency`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `237410`

Smoke and integration validation treat startup as complete once the server log
reaches the normal Source markers and `alphagsm info --json` reports `a2s`.

### Server Configuration

- **Config file**: `insurgency/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `embassy_coop checkpoint`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/insserver/](../server-templates/insserver/)

### Maps and Mods

- **Map directory**: `insurgency/maps/`
- **Mod directory**: `insurgency/addons/`
- **Workshop support**: Native item IDs/URLs and collection imports; live validation is described below.
- **Mod notes**: AlphaGSM can now manage Insurgency addons from checked-in `manifest` entries plus direct archive `url` entries, GameBanana ids, and Mod DB page URLs. The local manifest currently includes popular Source admin/plugin stacks such as MetaMod and SourceMod. Archives must unpack into approved addon paths under `insurgency/addons/`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/insurgency/`.
- **Map install**: Copy `.bsp` files into `insurgency/maps/` and add to `insurgency/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `insurgency/addons/`.

Examples:

```bash
alphagsm myins mod add manifest metamod
alphagsm myins mod add manifest sourcemod
alphagsm myins mod add url https://mods.example.invalid/ins-addon-pack.zip
alphagsm myins mod add gamebanana 12345
alphagsm myins mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
alphagsm myins mod apply
alphagsm myins mod cleanup
```


## Workshop server content

Add a public item ID or official Steam Community URL, or import a collection:

```bash
alphagsm myserver mod add workshop 498253639
alphagsm myserver mod add workshop-collection YOUR_COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

Collection imports are a snapshot of validated AppID `222880` items. AlphaGSM
uses the game's native `subscribed_file_ids.txt` list and `-workshop` startup
flag. No Workshop API key, Steam password or login token is supplied. The native
engine downloads and mounts current-format Workshop items; legacy uploads may
not work on Linux. Existing archive/manifest addon commands remain available.
See the [server-side Workshop guide](https://steamcommunity.com/sharedfiles/filedetails/?id=488818549).

Apply while the server is stopped, then start it. Only ID lines added by
AlphaGSM are removed by `mod cleanup`; operator IDs and comments remain.
Changing the whitespace or adding a comment to an owned ID line gives that line
to the operator. Engine-managed Workshop download caches are retained. Maps and
VPK theaters still need the appropriate map/mode or theater setting; subscribing
alone is not evidence that a running game loaded the content.

The opt-in checks require a fresh engine `path` probe containing every selected
item's mounted search path, then load a custom map and require its name in real
A2S `info --json`. The default fixture is
[this public map](https://steamcommunity.com/sharedfiles/filedetails/?id=498253639);
its Valve metadata was checked as public AppID `222880` on 2026-10-13.
The individual fixture passed the full AlphaGSM process and Docker lifecycles
on 2026-10-13, with native mount paths and A2S reporting the actual custom map.
Both runs used the normal stop-timeout fallback before shutdown was verified.
The collection fixture is [Connorhd's Server Maps](https://steamcommunity.com/sharedfiles/filedetails/?id=552903640),
containing three public current-format Insurgency maps. Both process and Docker
passed the collection lifecycle, with all three items mounted and the Amber
custom map reported by A2S.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_INSSERVER_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_insserver.py -k workshop

# Optional collection override, expanded without an API key:
# ALPHAGSM_INSSERVER_WORKSHOP_COLLECTION=YOUR_COLLECTION_ID
# ALPHAGSM_INSSERVER_WORKSHOP_MAP=your_custom_map
# ALPHAGSM_INSSERVER_WORKSHOP_MODE=checkpoint

ALPHAGSM_WORK_DIR=/path/on/large/disk INS_WORKSHOP_ITEM=498253639 \
make smoke-test SMOKE_TEST=run_insserver.sh
```

The smoke check supports `INS_WORKSHOP_COLLECTION`, `INS_WORKSHOP_MAP`
and `INS_WORKSHOP_MODE`. Docker checks use the `steamcmd-linux` image and
Source console terminal relay; set
`ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX` to the branch-local image tag when
validating repository changes.
