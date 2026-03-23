# Vintage Story

This guide covers the `vintagestoryserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvintages create vintagestoryserver
```

Run setup:

```bash
alphagsm myvintages setup
```

Start it:

```bash
alphagsm myvintages start
```

Check it:

```bash
alphagsm myvintages status
```

Stop it:

```bash
alphagsm myvintages stop
```

## Setup Details

Setup configures:

- the game port (default 42420)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myvintages update
alphagsm myvintages backup
```

## Notes

- Module name: `vintagestoryserver`
- Default port: 42420

## Developer Notes

### Run File

- **Executable**: `VintagestoryServer`
- **Location**: `<install_dir>/VintagestoryServer`
- **Engine**: Custom

### Server Configuration

- **Config files**: `serverconfig.json`
- **Template**: See [server-templates/vintagestoryserver/](../server-templates/vintagestoryserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
