# Call of Duty 4

This guide covers the `cod4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod4serv create cod4server
```

Run setup:

```bash
alphagsm mycod4serv setup
```

Start it:

```bash
alphagsm mycod4serv start
```

Check it:

```bash
alphagsm mycod4serv status
```

Stop it:

```bash
alphagsm mycod4serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycod4serv update
alphagsm mycod4serv backup
```

## Notes

- Module name: `cod4server`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `cod4_lnxded`
- **Location**: `<install_dir>/cod4_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/cod4server/](../server-templates/cod4server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
