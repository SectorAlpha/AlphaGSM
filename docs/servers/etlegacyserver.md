# ET: Legacy

This guide covers the `etlegacyserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

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
- downloads and extracts the server archive

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

## Developer Notes

### Run File

- **Executable**: `etlded.x86_64`
- **Location**: `<install_dir>/etlded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `etl_server.cfg`
- **Template**: See [server-templates/etlegacyserver/](../server-templates/etlegacyserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `sv_hostname` and `net_port` aligned with `set`

### Maps and Mods

- **Map directory**: `<fs_game>/` (default `legacy/`)
- **Mod directory**: `<fs_game>/` (default `legacy/`)
- **Mod notes**: AlphaGSM can now track direct `.pk3` and archive `url` entries for ET: Legacy, install approved `.pk3` payloads into the active `fs_game` directory, and clean up only AlphaGSM-managed files from `.alphagsm/mods/etlegacyserver/`.
- **Workshop support**: No
