# Call of Duty

This guide covers the `codserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycodserve create codserver
```

Run setup:

```bash
alphagsm mycodserve setup
```

Start it:

```bash
alphagsm mycodserve start
```

Check it:

```bash
alphagsm mycodserve status
```

Stop it:

```bash
alphagsm mycodserve stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycodserve update
alphagsm mycodserve backup
```

## Notes

- Module name: `codserver`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `cod_lnxded`
- **Location**: `<install_dir>/cod_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: `<moddir>/server.cfg` (default `main/server.cfg`)
- `set servername`, `set moddir`, and `set map` rewrite `<moddir>/server.cfg` immediately through the schema-backed config-sync path.
- **Template**: See [server-templates/codserver/](../server-templates/codserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
