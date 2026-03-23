# Battlefield Vietnam

This guide covers the `bfvserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybfvserve create bfvserver
```

Run setup:

```bash
alphagsm mybfvserve setup
```

Start it:

```bash
alphagsm mybfvserve start
```

Check it:

```bash
alphagsm mybfvserve status
```

Stop it:

```bash
alphagsm mybfvserve stop
```

## Setup Details

Setup configures:

- the game port (default 15567)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mybfvserve update
alphagsm mybfvserve backup
```

## Notes

- Module name: `bfvserver`
- Default port: 15567

## Developer Notes

### Run File

- **Executable**: `bfvietnam_lnxded`
- **Location**: `<install_dir>/bfvietnam_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/bfvserver/](../server-templates/bfvserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
