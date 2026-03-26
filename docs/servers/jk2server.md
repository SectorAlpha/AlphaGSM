# Jedi Knight II: Jedi Outcast

This guide covers the `jk2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myjk2serve create jk2server
```

Run setup:

```bash
alphagsm myjk2serve setup
```

Start it:

```bash
alphagsm myjk2serve start
```

Check it:

```bash
alphagsm myjk2serve status
```

Stop it:

```bash
alphagsm myjk2serve stop
```

## Setup Details

Setup configures:

- the game port (default 28070)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myjk2serve update
alphagsm myjk2serve backup
```

## Notes

- Module name: `jk2server`
- Default port: 28070

## Developer Notes

### Run File

- **Executable**: `jk2mvded.x86_64`
- **Location**: `<install_dir>/jk2mvded.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/jk2server/](../server-templates/jk2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
