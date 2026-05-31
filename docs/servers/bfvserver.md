# Battlefield Vietnam

This guide covers the `bfvserver` module in AlphaGSM.

## Requirements

- `screen`
- either a direct Battlefield Vietnam dedicated-server archive URL or a
  pre-staged Battlefield Vietnam Linux dedicated server tree
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

`bfvserver` is supported in `ENABLED (BYO)` mode. Before `setup` or `start`,
either:

- set `url` to a working Battlefield Vietnam dedicated-server archive, or
- stage `bfvietnam_lnxded` and the rest of the Battlefield Vietnam server
  files inside your chosen `<install_dir>/`

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
- downloads and extracts the server archive when `url` is set

Suggested flow:

```bash
alphagsm mybfvserve create bfvserver
alphagsm mybfvserve set url https://example.invalid/bfv-dedicated.run
alphagsm mybfvserve setup -n 15567 /path/to/bfv
alphagsm mybfvserve start
```

Or, if you already have the server files:

```bash
alphagsm mybfvserve create bfvserver
alphagsm mybfvserve setup -n 15567 /path/to/bfv
# copy bfvietnam_lnxded and the rest of the server tree into /path/to/bfv/
alphagsm mybfvserve start
```

## Useful Commands

```bash
alphagsm mybfvserve update
alphagsm mybfvserve backup
alphagsm mybfvserve set url https://example.invalid/bfv-dedicated.run
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
