# Terraria vanilla

This guide covers the `terraria.vanilla` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvanilla create terraria.vanilla
```

Run setup:

```bash
alphagsm myvanilla setup
```

Start it:

```bash
alphagsm myvanilla start
```

Check it:

```bash
alphagsm myvanilla status
```

Stop it:

```bash
alphagsm myvanilla stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myvanilla update
alphagsm myvanilla backup
```

## Notes

- Module name: `terraria.vanilla`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Linux/TerrariaServer.bin.x86_64`
- **Location**: `<install_dir>/Linux/TerrariaServer.bin.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/terraria-vanilla/](../server-templates/terraria-vanilla/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
