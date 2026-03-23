# Xonotic

This guide covers the `xntserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myxntserve create xntserver
```

Run setup:

```bash
alphagsm myxntserve setup
```

Start it:

```bash
alphagsm myxntserve start
```

Check it:

```bash
alphagsm myxntserve status
```

Stop it:

```bash
alphagsm myxntserve stop
```

## Setup Details

Setup configures:

- the game port (default 26000)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myxntserve update
alphagsm myxntserve backup
```

## Notes

- Module name: `xntserver`
- Default port: 26000

## Developer Notes

### Run File

- **Executable**: `xonotic-linux64-dedicated`
- **Location**: `<install_dir>/xonotic-linux64-dedicated`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/xntserver/](../server-templates/xntserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
