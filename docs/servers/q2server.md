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
```

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
- `set servername` and `set map` rewrite `<gamedir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/q2server/](../server-templates/q2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
