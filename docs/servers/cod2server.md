# Call of Duty 2

This guide covers the `cod2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod2serv create cod2server
```

Run setup:

```bash
alphagsm mycod2serv setup
```

Start it:

```bash
alphagsm mycod2serv start
```

Check it:

```bash
alphagsm mycod2serv status
```

Stop it:

```bash
alphagsm mycod2serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycod2serv update
alphagsm mycod2serv backup
```

## Notes

- Module name: `cod2server`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `cod2_lnxded`
- **Location**: `<install_dir>/cod2_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/cod2server/](../server-templates/cod2server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/`
- **Workshop support**: No

## Mod Sources

Call of Duty 2 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir` directory, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm mycod2serv mod add url https://example.com/mappack.pk3
alphagsm mycod2serv mod add url https://example.com/custom-content.zip
alphagsm mycod2serv mod apply
alphagsm mycod2serv mod cleanup
```
