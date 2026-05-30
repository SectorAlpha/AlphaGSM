# Xonotic

This guide covers the `xntserver` module in AlphaGSM.

Current status: PASSED 2026-05-30. The validated lifecycle now covers the
shared `quake-linux` Docker runtime as well as the module's Quake
`query` / `info` surface.

## Requirements

- Docker for the validated container-backed Linux runtime, or a compatible local process runtime
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

- **Launcher**: `server/server_linux.sh`
- **Runtime binary**: `xonotic-linux64-dedicated`
- **Location**: `<install_dir>/server/server_linux.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: AlphaGSM writes the managed dedicated config to `<install_dir>/data/server.cfg`
- **Template**: See [server-templates/xntserver/](../server-templates/xntserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
