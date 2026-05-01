# Call of Duty: World at War

This guide covers the `codwawserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycodwawse create codwawserver
```

Run setup:

```bash
alphagsm mycodwawse setup
```

Start it:

```bash
alphagsm mycodwawse start
```

Check it:

```bash
alphagsm mycodwawse status
```

Stop it:

```bash
alphagsm mycodwawse stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycodwawse update
alphagsm mycodwawse backup
```

## Notes

- Module name: `codwawserver`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `codwaw_lnxded`
- **Location**: `<install_dir>/codwaw_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/codwawserver/](../server-templates/codwawserver/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/`
- **Workshop support**: No

## Mod Sources

Call of Duty: World at War supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mycodwawse mod add url https://example.com/mappack.pk3
alphagsm mycodwawse mod add url https://example.com/custom-content.zip
alphagsm mycodwawse mod apply
alphagsm mycodwawse mod cleanup
```
