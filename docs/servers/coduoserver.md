# Call of Duty: United Offensive

This guide covers the `coduoserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycoduoser create coduoserver
```

Run setup:

```bash
alphagsm mycoduoser setup
```

Start it:

```bash
alphagsm mycoduoser start
```

Check it:

```bash
alphagsm mycoduoser status
```

Stop it:

```bash
alphagsm mycoduoser stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycoduoser update
alphagsm mycoduoser backup
```

## Notes

- Module name: `coduoserver`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `coduoded_lnxded`
- **Location**: `<install_dir>/coduoded_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `uo/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/coduoserver/](../server-templates/coduoserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
