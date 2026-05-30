# Aloft

This guide covers the `aloftserver` module in AlphaGSM.

## Requirements

- `screen`
- an owned Aloft dedicated-server tree
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

`aloftserver` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
copy an owned Aloft server tree into your chosen `<install_dir>/` so
`<install_dir>/AloftServerNoGuiLoad.ps1` exists.

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

- the game port (default 0 unless you set one explicitly)
- the install directory

Suggested flow:

```bash
alphagsm myaloftser create aloftserver
alphagsm myaloftser setup -n 27015 /path/to/aloftserver
# copy the owned Aloft server files into /path/to/aloftserver/
alphagsm myaloftser start
```

## Useful Commands

```bash
alphagsm myaloftser update
alphagsm myaloftser backup
```

## Notes

- Module name: `aloftserver`
- Default port: `0` unless explicitly set during setup

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
