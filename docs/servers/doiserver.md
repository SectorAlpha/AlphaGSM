# Day of Infamy

This guide covers the `doiserver` module in AlphaGSM.

`doiserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create doiserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `bastogne stronghold`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `32`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Day of Infamy`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

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
- **Workshop support**: Native item IDs/URLs and collection imports; live validation is described below.
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/doi/`.
- **Map install**: Copy `.bsp` files into `doi/maps/` and add to `doi/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `doi/addons/`.


## Workshop server content

Add a public item ID or official Steam Community URL, or import a collection:

```bash
alphagsm myserver mod add workshop 823752012
alphagsm myserver mod add workshop-collection YOUR_COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver start
```

Collection imports are a snapshot of validated AppID `447820` items. AlphaGSM
uses the game's native `subscribed_file_ids.txt` list and `-workshop` startup
flag. No Workshop API key, Steam password or login token is supplied. The native
engine downloads and mounts current-format Workshop items; legacy uploads may
not work on Linux. Existing archive/manifest addon commands remain available.
See the [server-side Workshop guide](https://steamcommunity.com/sharedfiles/filedetails/?id=952463590).

Apply while the server is stopped, then start it. Only ID lines added by
AlphaGSM are removed by `mod cleanup`; operator IDs and comments remain.
Changing the whitespace or adding a comment to an owned ID line gives that line
to the operator. Engine-managed Workshop download caches are retained. Maps and
VPK theaters still need the appropriate map/mode or theater setting; subscribing
alone is not evidence that a running game loaded the content.

The opt-in checks require a fresh engine `path` probe containing every selected
item's mounted search path, then load a custom map and require its name in real
A2S `info --json`. The default fixture is
[this public map](https://steamcommunity.com/sharedfiles/filedetails/?id=823752012);
its Valve metadata was checked as public AppID `447820` on 2026-10-13.
The Stalingrad fixture passed the full AlphaGSM process and Docker lifecycles
on 2026-10-13, with fresh native mount paths and A2S reporting the custom map.
Both runs used the normal stop-timeout fallback before shutdown was verified.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_DOISERVER_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_doiserver.py -k workshop

# Optional collection override, expanded without an API key:
# ALPHAGSM_DOISERVER_WORKSHOP_COLLECTION=YOUR_COLLECTION_ID
# ALPHAGSM_DOISERVER_WORKSHOP_MAP=your_custom_map
# ALPHAGSM_DOISERVER_WORKSHOP_MODE=offensive

ALPHAGSM_WORK_DIR=/path/on/large/disk DOI_WORKSHOP_ITEM=823752012 \
make smoke-test SMOKE_TEST=run_doiserver.sh
```

The smoke check supports `DOI_WORKSHOP_COLLECTION`, `DOI_WORKSHOP_MAP`
and `DOI_WORKSHOP_MODE`. Docker checks use the `steamcmd-linux` image and
Source console terminal relay; set
`ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX` to the branch-local image tag when
validating repository changes.
