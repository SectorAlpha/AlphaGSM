# Call of Duty 4

This guide covers the `cod4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod4serv create cod4server
```

Run setup:

```bash
alphagsm mycod4serv setup
```

Start it:

```bash
alphagsm mycod4serv start
```

Check it:

```bash
alphagsm mycod4serv status
```

Stop it:

```bash
alphagsm mycod4serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycod4serv update
alphagsm mycod4serv backup
```

## Notes

- Module name: `cod4server`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `cod4_lnxded`
- **Location**: `<install_dir>/cod4_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/cod4server/](../server-templates/cod4server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<moddir>/`
- **Mod directory**: `<install_dir>/<moddir>/` (default `<install_dir>/main/`)
- **Workshop support**: No

## Mod Sources

Call of Duty 4 supports AlphaGSM-managed direct `url` mod sources for content-only `.pk3` payloads.

Supported payload shapes:

- a direct `.pk3` URL
- an archive containing bare `.pk3` files at the archive root
- an archive containing `<moddir>/<name>.pk3`

AlphaGSM installs approved `.pk3` content into the active `moddir`, tracks only the files it owns, and keeps the active `moddir` in the managed backup targets.

Examples:

```bash
alphagsm mycod4serv mod add url https://example.com/custom.pk3
alphagsm mycod4serv mod add url https://example.com/custom-pack.zip
alphagsm mycod4serv mod apply
alphagsm mycod4serv mod cleanup
```
