# ET: Legacy

This guide covers the `etlegacyserver` module in AlphaGSM.

`etlegacyserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection around that owned-base-assets
prerequisite, while local runs remain process-backed by default unless you opt
into the Docker backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`
- Stock Wolfenstein: Enemy Territory multiplayer packs in `etmain/`
  - Required files: `etmain/pak0.pk3`, `etmain/pak1.pk3`, and `etmain/pak2.pk3`
  - `setup` stages only those three packs from the official Splash Damage freeware archive
  - `pak0.pk3` alone is not enough

## Quick Start

Create the server:

```bash
alphagsm myetlegacy create etlegacyserver
```

Run setup:

```bash
alphagsm myetlegacy setup
```

Start it:

```bash
alphagsm myetlegacy start
```

Check it:

```bash
alphagsm myetlegacy status
```

Stop it:

```bash
alphagsm myetlegacy stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the ET: Legacy engine archive
- stages `etmain/pak0.pk3`, `etmain/pak1.pk3`, and `etmain/pak2.pk3` from the official Splash Damage freeware full-game archive
- does not install the original client, PunkBuster, videos, or etkey tools
- installs the public ET: Legacy engine and `legacy/` mod bundle

This server is supported in `ENABLED (BYO)` mode. The engine download does not include the stock packs. `setup` copies only the three multiplayer packs out of the official freeware archive. A tree that contains `pak0.pk3` without `pak1.pk3` and `pak2.pk3` is still rejected. Without `etmain/pak0.pk3`, the dedicated server exits at `FS_InitFilesystem: Original game data files not found`.

A local process run on 2026-10-16 answered Quake status on UDP 57831 (`oasis`, hostname ET: Legacy Host, 0/24) and stopped. Docker was not rerun. The stock multiplayer maps in those packs are `battery`, `fueldump`, `goldrush`, `oasis`, `radar`, and `railgun`.

## Useful Commands

```bash
alphagsm myetlegacy update
alphagsm myetlegacy backup
alphagsm myetlegacy set servername "AlphaGSM ET"
alphagsm myetlegacy set port 27961
```

`set servername` and `set port` rewrite `etl_server.cfg` immediately through the schema-backed config-sync path.

## Mod Sources

ET: Legacy content management currently targets the active `fs_game`
directory under the server root. By default that is `legacy/`, but if you set
a custom `fs_game` value, AlphaGSM installs into that directory instead.

- Current mod source support is direct `url` entries only.
- `mod add url <https-url>` accepts direct `.pk3` URLs and supported archive URLs such as `.zip`, `.7z`, or tar variants when the payload exposes either `<fs_game>/<name>.pk3` or bare `.pk3` files at the archive root.
- `mod cleanup` removes only AlphaGSM-tracked `.pk3` files and keeps its cache/state under `.alphagsm/mods/etlegacyserver/`.
- The first ET: Legacy slice intentionally stops at `.pk3` content and does not try to install arbitrary extracted scripts or binaries.

Examples:

```bash
alphagsm myetlegacy mod add url https://example.invalid/mappack.zip
alphagsm myetlegacy mod add url https://example.invalid/pak-custom.pk3
alphagsm myetlegacy mod apply
alphagsm myetlegacy mod cleanup
```

## Notes

- Module name: `etlegacyserver`
- Default port: 27960

<!-- alphagsm-server-variables:start -->

## Server variables

After `create etlegacyserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `configfile` | — | string | Server config file to exec on startup. |
| `dir` | — | string | Install directory for the server. |
| `download_name` | — | string | Cached archive filename. |
| `exe_name` | — | string | Server executable filename. |
| `fs_game` | — | string | The active game/mod directory. Example: `baseq3`. |
| `hostname` | servername, name | string | The advertised server name. |
| `port` | gameport | integer | The game port for the server. |
| `url` | — | string | Download URL for the server archive. |
| `version` | — | string | Requested upstream release version. |

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `etlded.x86_64`
- **Location**: `<install_dir>/etlded.x86_64`
- **Engine**: Custom
- **Stock packs staged by install**: `etmain/pak0.pk3`, `etmain/pak1.pk3`, and `etmain/pak2.pk3` from the official Splash Damage freeware archive. `pak0.pk3` alone is rejected.

### Server Configuration

- **Config file**: `etl_server.cfg`
- **Template**: See [server-templates/etlegacyserver/](../server-templates/etlegacyserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `sv_hostname` and `net_port` aligned with `set`

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `legacy/`)
- **Mod directory**: `<fs_game>/` (default `legacy/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for ET: Legacy, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/etlegacyserver/`.
- **Workshop support**: No

## BYO file helper

Inspect this game's required files, source instructions and destinations with
`alphagsm <server-name> assets requirements`; check the declared files with
`alphagsm <server-name> assets check`. File checks do not establish game readiness.
This module has an allowlisted local import recipe. Use its source instructions to prepare the required data before importing.
See [BYO files and private SteamCMD acquisition](../byo-files.md).
