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
- **Workshop support**: No
- **Mod notes**: AlphaGSM can now manage Garry's Mod addons from checked-in `manifest` entries plus direct `url` entries, GameBanana ids, and Mod DB page URLs. The local manifest currently includes popular admin/plugin stacks such as MetaMod, SourceMod, ULib, ULX, and AdvDupe2. Direct URLs can point at `.gma` files or supported archives; provider-backed sources currently install supported archives only, while checked-in manifest entries can now install either supported archives or single-file `.gma` assets. Garry's Mod addon archives that unpack as a bare addon root are installed under `garrysmod/addons/<family-or-archive-name>/`, so `ulx` can also pull in its checked-in `ulib` dependency automatically. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps its cache/state under `.alphagsm/mods/gmodserver/`.
- **Map install**: Copy `.bsp` files into `garrysmod/maps/` and add to `garrysmod/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `garrysmod/addons/`.

Examples:

```bash
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
