# QuakeWorld

This guide covers the `qwserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myqwserver create qwserver
```

Run setup:

```bash
alphagsm myqwserver setup
```

Start it:

```bash
alphagsm myqwserver start
```

Check it:

```bash
alphagsm myqwserver status
```

Stop it:

```bash
alphagsm myqwserver stop
```

## Setup Details

Setup configures:

- the game port (default 27500)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myqwserver update
alphagsm myqwserver backup
```

## Notes

- Module name: `qwserver`
- Default port: 27500

## Developer Notes

### Run File

- **Executable**: `mvdsv`
- **Location**: `<install_dir>/mvdsv`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/qwserver/](../server-templates/qwserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
