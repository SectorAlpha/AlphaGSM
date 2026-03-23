# Quake 3 Arena

This guide covers the `q3server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq3server create q3server
```

Run setup:

```bash
alphagsm myq3server setup
```

Start it:

```bash
alphagsm myq3server start
```

Check it:

```bash
alphagsm myq3server status
```

Stop it:

```bash
alphagsm myq3server stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq3server update
alphagsm myq3server backup
```

## Notes

- Module name: `q3server`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `q3ded.x86_64`
- **Location**: `<install_dir>/q3ded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/q3server/](../server-templates/q3server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
