# Skyrim Together Reborn

This guide covers the `skyrimtogetherrebornserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myskyrimto create skyrimtogetherrebornserver
```

Run setup:

```bash
alphagsm myskyrimto setup
```

Start it:

```bash
alphagsm myskyrimto start
```

Check it:

```bash
alphagsm myskyrimto status
```

Stop it:

```bash
alphagsm myskyrimto stop
```

## Setup Details

Setup configures:

- the game port (default 10578)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myskyrimto update
alphagsm myskyrimto backup
```

## Notes

- Module name: `skyrimtogetherrebornserver`
- Default port: 10578

## Developer Notes

### Run File

- **Executable**: `SkyrimTogetherServer`
- **Location**: `<install_dir>/SkyrimTogetherServer`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/skyrimtogetherrebornserver/](../server-templates/skyrimtogetherrebornserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
