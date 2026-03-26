# Aloft

This guide covers the `aloftserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaloftser create aloftserver
```

Run setup:

```bash
alphagsm myaloftser setup
```

Start it:

```bash
alphagsm myaloftser start
```

Check it:

```bash
alphagsm myaloftser status
```

Stop it:

```bash
alphagsm myaloftser stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm myaloftser update
alphagsm myaloftser backup
```

## Notes

- Module name: `aloftserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `AloftServerNoGuiLoad.ps1`
- **Location**: `<install_dir>/AloftServerNoGuiLoad.ps1`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/aloftserver/](../server-templates/aloftserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
