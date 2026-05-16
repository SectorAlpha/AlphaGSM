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

- **Map directory**: `<install_dir>/qw/maps/`
- **Mod directory**: `<install_dir>/qw/`
- **Workshop support**: No

## Mod Sources

QuakeWorld supports AlphaGSM-managed direct `url` mod sources for content-only `.pak` payloads.

Supported payload shapes:

- a direct `.pak` URL
- an archive containing bare `.pak` files at the archive root
- an archive containing `qw/<name>.pak`

AlphaGSM installs approved `.pak` content into `qw/`, tracks only the files it owns, and keeps that content directory in the managed backup targets.

Examples:

```bash
alphagsm myqwserver mod add url https://example.com/pak1.pak
alphagsm myqwserver mod add url https://example.com/custom-content.zip
alphagsm myqwserver mod apply
alphagsm myqwserver mod cleanup
```
