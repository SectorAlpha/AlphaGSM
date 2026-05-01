# Quake 4

This guide covers the `q4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq4server create q4server
```

Run setup:

```bash
alphagsm myq4server setup
```

Start it:

```bash
alphagsm myq4server start
```

Check it:

```bash
alphagsm myq4server status
```

Stop it:

```bash
alphagsm myq4server stop
```

## Setup Details

Setup configures:

- the game port (default 28004)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq4server update
alphagsm myq4server backup
alphagsm myq4server set servername "AlphaGSM Q4"
alphagsm myq4server set map q4dm6
```

`set servername`, `set fs_game`, and `set map` rewrite `<fs_game>/server.cfg` immediately through the schema-backed config-sync path.

## Notes

- Module name: `q4server`
- Default port: 28004

## Developer Notes

### Run File

- **Executable**: `q4ded.x86`
- **Location**: `<install_dir>/q4ded.x86`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<fs_game>/server.cfg` (default `q4base/server.cfg`)
- **Template**: See [server-templates/q4server/](../server-templates/q4server/) if available
- **Schema-backed sync**: AlphaGSM keeps `hostname`, `fs_game`, and `startmap` aligned with `set`

### Maps and Mods

- **Map directory**: `<install_dir>/<fs_game>/`
- **Mod directory**: `<install_dir>/<fs_game>/`
- **Workshop support**: No

## Mod Sources

Quake 4 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk4` payloads.

Supported payload shapes:

- a direct `.pk4` URL
- an archive containing bare `.pk4` files at the archive root
- an archive containing `<fs_game>/<name>.pk4`

AlphaGSM installs approved `.pk4` content into the active `fs_game` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myq4server mod add url https://example.com/mappack.pk4
alphagsm myq4server mod add url https://example.com/custom-content.zip
alphagsm myq4server mod apply
alphagsm myq4server mod cleanup
```
