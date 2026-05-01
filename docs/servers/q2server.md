# Quake 2

This guide covers the `q2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq2server create q2server
```

Run setup:

```bash
alphagsm myq2server setup
```

Start it:

```bash
alphagsm myq2server start
```

Check it:

```bash
alphagsm myq2server status
```

Stop it:

```bash
alphagsm myq2server stop
```

## Setup Details

Setup configures:

- the game port (default 27910)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq2server update
alphagsm myq2server backup
alphagsm myq2server set servername "AlphaGSM Q2"
alphagsm myq2server set gamedir custom
alphagsm myq2server set map q2dm8
```

`set servername`, `set gamedir`, and `set map` rewrite `<gamedir>/server.cfg` immediately through the schema-backed config-sync path.

## Notes

- Module name: `q2server`
- Default port: 27910

## Developer Notes

### Run File

- **Executable**: `q2ded`
- **Location**: `<install_dir>/q2ded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<gamedir>/server.cfg` (default `baseq2/server.cfg`)
- **Schema-backed sync**: AlphaGSM keeps `hostname`, `gamedir`, and `startmap` aligned with `set`
- **Template**: See [server-templates/q2server/](../server-templates/q2server/) if available

### Maps and Mods

- **Map directory**: `<install_dir>/<gamedir>/`
- **Mod directory**: `<install_dir>/<gamedir>/`
- **Workshop support**: No

## Mod Sources

Quake 2 supports AlphaGSM-managed direct `url` mod sources for content-only `.pak` payloads.

Supported payload shapes:

- a direct `.pak` URL
- an archive containing bare `.pak` files at the archive root
- an archive containing `<gamedir>/<name>.pak`

AlphaGSM installs approved `.pak` content into the active `gamedir`, tracks only the files it owns, and adds that active content directory to the managed backup targets.

Examples:

```bash
alphagsm myq2server mod add url https://example.com/pak1.pak
alphagsm myq2server mod add url https://example.com/custom-content.zip
alphagsm myq2server mod apply
alphagsm myq2server mod cleanup
```
