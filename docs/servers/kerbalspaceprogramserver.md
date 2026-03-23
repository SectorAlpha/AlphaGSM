# Kerbal Space Program community

This guide covers the `kerbalspaceprogramserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykerbalsp create kerbalspaceprogramserver
```

Run setup:

```bash
alphagsm mykerbalsp setup
```

Start it:

```bash
alphagsm mykerbalsp start
```

Check it:

```bash
alphagsm mykerbalsp status
```

Stop it:

```bash
alphagsm mykerbalsp stop
```

## Setup Details

Setup configures:

- the game port (default 8800)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mykerbalsp update
alphagsm mykerbalsp backup
```

## Notes

- Module name: `kerbalspaceprogramserver`
- Default port: 8800

## Developer Notes

### Run File

- **Executable**: `Server`
- **Location**: `<install_dir>/Server`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/kerbalspaceprogramserver/](../server-templates/kerbalspaceprogramserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
