# No More Room in Hell

This guide covers the `nmrihserver` module in AlphaGSM.

`nmrihserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynmrihser create nmrihserver
```

Run setup:

```bash
alphagsm mynmrihser setup
```

Start it:

```bash
alphagsm mynmrihser start
```

Check it:

```bash
alphagsm mynmrihser status
```

Stop it:

```bash
alphagsm mynmrihser stop
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
alphagsm mynmrihser update
alphagsm mynmrihser backup
```

## Notes

- Module name: `nmrihserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create nmrihserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `nmo_broadway`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `8`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM No More Room in Hell`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `317670`

### Server Configuration

- **Config file**: `nmrih/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `nmo_broadway`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/nmrihserver/](../server-templates/nmrihserver/)

### Maps and Mods

- **Map directory**: `nmrih/maps/`
- **Mod directory**: `nmrih/addons/`
- **Workshop support**: Anonymous dedicated map items by ID/URL and same-game collections.
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/nmrih/`.
- **Map install**: Copy `.bsp` files into `nmrih/maps/` and add to `nmrih/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nmrih/addons/`.


## Workshop multiplayer maps

Add a public dedicated map item or a Steam Community item URL. Collections expand
into a snapshot of same-game item IDs:

```bash
alphagsm myserver mod add workshop 3514998402
alphagsm myserver mod add workshop-collection YOUR_COLLECTION_ID
alphagsm myserver mod apply
alphagsm myserver set map nmo_lotr_mines_of_moria_v3
alphagsm myserver start
```

SteamCMD downloads these maps anonymously using the game's AppID `224260`.
AlphaGSM validates Source BSP headers and map-family names, then publishes map
assets into `nmrih/maps/` and approved native asset directories. Packages
must contain dedicated maps; client-only reskins and other-game maps are rejected.
The original archive-backed addon commands remain available.

Apply and clean up while the server is stopped. AlphaGSM refuses unowned file
collisions and removes only unchanged files recorded by its Workshop map owner.
If you edit a managed asset, restore its installed bytes before reapplying or
cleaning up. Download caches remain in `.alphagsm/workshop/`.

This activates native server map assets. Players must subscribe to the matching
Workshop item or receive the required map assets through your own supported
content delivery configuration. AlphaGSM does not configure automatic Workshop
client delivery for these maps.

The public [Mines of Moria fixture](https://steamcommunity.com/sharedfiles/filedetails/?id=3514998402)
was checked against Valve metadata for AppID `224260` on 2026-10-13. The process
lifecycle passed on 2026-10-13, with real A2S reporting `nmo_lotr_mines_of_moria_v3`,
verified shutdown and owned-asset cleanup. Docker validation is pending an
SSD-backed Docker endpoint. Opt-in lifecycle tests load this custom map
through the running engine and require real A2S `info --json` to report its name;
file staging alone cannot pass the load check.

```bash
ALPHAGSM_WORK_DIR=/path/on/large/disk \
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_NMRIHSERVER_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_nmrihserver.py -k workshop

ALPHAGSM_WORK_DIR=/path/on/large/disk NMRIH_WORKSHOP_ITEM=3514998402 \
make smoke-test SMOKE_TEST=run_nmrihserver.sh
```

The checks accept `ALPHAGSM_NMRIHSERVER_WORKSHOP_COLLECTION` and
`ALPHAGSM_NMRIHSERVER_WORKSHOP_MAP` overrides. Smoke uses
`NMRIH_WORKSHOP_COLLECTION` and `NMRIH_WORKSHOP_MAP`. Process and Docker
checks use the same AlphaGSM lifecycle; Docker uses the `steamcmd-linux` image
and Source console terminal relay. Set
`ALPHAGSM_BACKEND_DOCKER_IMAGE_STEAMCMD_LINUX` to the branch-local image tag when
validating repository changes.
