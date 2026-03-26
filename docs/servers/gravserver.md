# GRAV

This guide covers the `gravserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygravserv create gravserver
```

Run setup:

```bash
alphagsm mygravserv setup
```

Start it:

```bash
alphagsm mygravserv start
```

Check it:

```bash
alphagsm mygravserv status
```

Stop it:

```bash
alphagsm mygravserv stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory

## Useful Commands

```bash
alphagsm mygravserv update
alphagsm mygravserv backup
```

## Notes

- Module name: `gravserver`
- Default port: 7778

## Developer Notes

### Run File

- **Executable**: `CAGGameServer-Win32-Shipping`
- **Location**: `<install_dir>/CAGGameServer-Win32-Shipping`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/gravserver/](../server-templates/gravserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
