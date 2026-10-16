# Garrys Mod

This guide covers the `gmodserver` module in AlphaGSM.

`gmodserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

AlphaGSM prefers the installed `srcds_run_64` or `srcds_run` wrapper so the
engine can load its bundled shared libraries. An explicit executable override
continues to take precedence.
If an existing installation saved `srcds_linux64`, run
`alphagsm mygmodserv set exe_name srcds_run` before starting it to restore the
wrapper's library setup.

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygmodserv create gmodserver
```

Run setup:

```bash
alphagsm mygmodserv setup
```

Start it:

```bash
alphagsm mygmodserv start
```

Check it:

```bash
alphagsm mygmodserv status
```

Stop it:

```bash
alphagsm mygmodserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- SteamCMD also downloads common mountable Source content into `_gmod_content/`
- default configuration and backup settings

Startup prefers the server's own launcher before searching downloaded game
content. This keeps bundled TF2 launchers from changing the server's working
directory in process and Docker runtimes.

## Useful Commands

```bash
alphagsm mygmodserv update
alphagsm mygmodserv backup
```

## Notes

- Module name: `gmodserver`
- Default port: 27015

<!-- alphagsm-server-variables:start -->

## Server variables

After `create gmodserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `map` | gamemap, startmap, level, worldname | string | The currently selected map or level. Example: `gm_construct`. |
| `maxplayers` | users | integer | Maximum number of player slots. Example: `16`. |
| `port` | gameport | integer | The primary game port. Example: `27015`. |
| `rconpassword` | rconpass, querypassword, query_administrator_password | string | Remote console password for administrative access. Stored as a secret. |
| `servername` | hostname, name | string | The server's public name shown to players. Example: `AlphaGSM Garrys Mod`. |
| `serverpassword` | sv_password, password | string | Password required for players to join the server. Stored as a secret. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `4020`

### Server Configuration

- **Config file**: `garrysmod/cfg/server.cfg`
- **Mount config**: `garrysmod/cfg/mount.cfg`
- **Depot config**: `garrysmod/cfg/mountdepots.txt`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `gm_construct`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/gmodserver/](../server-templates/gmodserver/)

### Maps and Mods

- **Map directory**: `garrysmod/maps/`
- **Mod directory**: `garrysmod/addons/`
- **Mounted base content**: AlphaGSM installs common Source content under `_gmod_content/`
  and writes default mounts for Counter-Strike: Source, Half-Life 2: Deathmatch,
  and Team Fortress 2.
- **Workshop support**: Individual IDs, official Steam Community URLs, and collection imports through `mod add workshop` / `mod add workshop-collection`.
- **Mod notes**: AlphaGSM can now manage Garry's Mod addons from checked-in `manifest` entries plus direct `url` entries, GameBanana ids, and Mod DB page URLs. The local manifest currently includes popular admin/plugin stacks such as MetaMod, SourceMod, ULib, ULX, and AdvDupe2. Direct URLs can point at `.gma` files or supported archives; GameBanana and Mod DB currently install supported archives only, while checked-in manifest entries can now install either supported archives or single-file `.gma` assets. Garry's Mod addon archives that unpack as a bare addon root are installed under `garrysmod/addons/<family-or-archive-name>/`, so `ulx` can also pull in its checked-in `ulib` dependency automatically. `mod cleanup` removes only AlphaGSM-tracked addon files, clears its desired entries, and removes its addon cache under `.alphagsm/mods/gmodserver/`.
- **Map install**: Copy `.bsp` files into `garrysmod/maps/` and add to `garrysmod/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `garrysmod/addons/`.

Workshop items are checked against the game AppID `4000` before being added or
applied (the dedicated-server download uses AppID `4020`). Collection imports
expand public same-game collections into item desired state; later collection
changes require another import. Only a single regular version-3 `.gma` payload
is accepted per Workshop item. AlphaGSM validates its file table, paths, bounds
and available CRCs before extracting it under `garrysmod/addons/<workshop-id>/`.
The dedicated engine loads this addon folder at the next start. Direct URL and
manifest GMA payloads use the same validation and extraction path.
`start` applies enabled desired addons automatically unless `mods.autoapply` is
false. Downloads use anonymous SteamCMD; unavailable, private, or entitlement-gated
items fail with the provider's error. Stop a running server before applying or
cleaning up addons, then start it again to reload mounted content.

This uses the same addon desired state and cleanup as manifest/URL addons.
It does not write `srcds_workshop_ids.txt` or add `host_workshop_collection` to the
launch command. Those are separate native download paths described in the
[Facepunch dedicated-server Workshop guide](https://wiki.facepunch.com/gmod/Workshop_for_Dedicated_Servers).
For client-required assets, follow Facepunch's
[content serving guidance](https://wiki.facepunch.com/gmod/Serving_Content).

Examples:

```bash
alphagsm mygmod mod add workshop 557962238
alphagsm mygmod mod add workshop https://steamcommunity.com/sharedfiles/filedetails/?id=557962238
alphagsm mygmod mod add workshop-collection YOUR_PUBLIC_COLLECTION_ID
alphagsm mygmod mod remove workshop 557962238
alphagsm mygmod mod add manifest metamod
alphagsm mygmod mod add manifest sourcemod
alphagsm mygmod mod add manifest ulib
alphagsm mygmod mod add manifest ulx
alphagsm mygmod mod add manifest advdupe2
alphagsm mygmod mod add url https://addons.example.invalid/example-addon.gma
alphagsm mygmod mod add gamebanana 12345
alphagsm mygmod mod add moddb https://www.moddb.com/mods/example/downloads/example-addon-pack
alphagsm mygmod mod apply
alphagsm mygmod mod cleanup
```

### Extra Content Notes

- Facepunch recommends installing extra mounted content outside the server root; AlphaGSM follows that pattern with `_gmod_content/`.
- `mountdepots.txt` is seeded with the default Garry's Mod depot set, including `hl1`, `hl1_hd`, `hl2`, `episodic`, `ep2`, and `lostcoast`.
- Single-player Valve games such as Episode One, Episode Two, and Lost Coast still require an owned Steam account if you want to download their content manually.

### Verify Workshop loading

The opt-in integration checks run the full AlphaGSM lifecycle in both process
and Docker runtimes and load a fresh test-owned Lua probe through the running server console. They
require the engine
[virtual filesystem](https://wiki.facepunch.com/gmod/file.Read) to expose an
addon-only file with the expected CRC for every selected item, and require the
ULib and ULX fixtures to initialize their `ULib.ucl.query` and `ulx.command` APIs. Downloaded files alone do
not count as successful loading. The test script avoids Source console input
length limits and matches only a completed nonce-bearing probe. The default small fixture is the official
[ULib server addon](https://steamcommunity.com/sharedfiles/filedetails/?id=557962238);
Valve's metadata reported public AppID `4000`, title `ULib`, and size 246,309 bytes
on 2026-10-13. The default collection fixture is
[sandbox server](https://steamcommunity.com/sharedfiles/filedetails/?id=2886432224),
whose public Valve collection response contained ULib and ULX on the same date.
The full AlphaGSM collection lifecycle passed in process and Docker runtimes on
2026-10-13, including fresh API evidence for both addons and verified shutdown.
The Docker run used the normal forced shutdown fallback after its stop timeout.

```bash
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_RUN_GMOD_WORKSHOP=1 \
python3 -m pytest tests/integration_tests/test_gmodserver.py -k workshop

# Import and verify every item from your selected collection:
ALPHAGSM_RUN_INTEGRATION=1 ALPHAGSM_RUN_STEAMCMD=1 \
ALPHAGSM_GMOD_WORKSHOP_COLLECTION=YOUR_PUBLIC_COLLECTION_ID \
python3 -m pytest tests/integration_tests/test_gmodserver.py -k workshop_collection

ALPHAGSM_WORK_DIR=/path/with/enough/space GMOD_WORKSHOP_ITEM=557962238 \
make smoke-test SMOKE_TEST=run_gmodserver.sh
# Or use GMOD_WORKSHOP_COLLECTION=YOUR_PUBLIC_COLLECTION_ID.
```

Docker validation needs the local `steamcmd-linux` runtime image and daemon.
An unavailable image or provider download is an unverified prerequisite;
engine-probe timeouts remain failures.
