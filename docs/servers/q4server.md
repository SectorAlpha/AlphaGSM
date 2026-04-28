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

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
