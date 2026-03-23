# TShock

This guide covers the `terraria.tshock` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytshock create terraria.tshock
```

Run setup:

```bash
alphagsm mytshock setup
```

Start it:

```bash
alphagsm mytshock start
```

Check it:

```bash
alphagsm mytshock status
```

Stop it:

```bash
alphagsm mytshock stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mytshock update
alphagsm mytshock backup
```

## Notes

- Module name: `terraria.tshock`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `TShock.Server.dll`
- **Location**: `<install_dir>/TShock.Server.dll`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/terraria-tshock/](../server-templates/terraria-tshock/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
