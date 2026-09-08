# Terraria vanilla

This guide covers the `terraria.vanilla` module in AlphaGSM.

`terraria.vanilla` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvanilla create terraria.vanilla
```

Run setup:

```bash
alphagsm myvanilla setup
```

Create its first world and start it:

```bash
alphagsm myvanilla start --autocreate
```

Check it:

```bash
alphagsm myvanilla status
```

Stop it:

```bash
alphagsm myvanilla stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- downloads and extracts the server archive

## World Selection and Reset

`start --autocreate` creates the configured world only when it is missing.
If the world already exists, the option does nothing and startup behaves like
plain `start`. Use `alphagsm myvanilla connect` to answer the native console prompts.

To start over, stop the server and run `alphagsm myvanilla reset-world`.
It lists the world data to delete and asks for confirmation; `-Y` bypasses
that prompt. `wipe` is an alias for the same operation.

See [world creation and reset](../world-management.md) for settings, supported
paths, and the full lifecycle.

## Useful Commands

```bash
alphagsm myvanilla update
alphagsm myvanilla backup
```

## Notes

- Module name: `terraria.vanilla`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Linux/TerrariaServer.bin.x86_64`
- **Location**: `<install_dir>/Linux/TerrariaServer.bin.x86_64`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/terraria-vanilla/](../server-templates/terraria-vanilla/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
