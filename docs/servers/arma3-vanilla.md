# Namespaced Arma 3 vanilla

This guide covers the `arma3.vanilla` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvanilla create arma3.vanilla
```

Run setup:

```bash
alphagsm myvanilla setup
```

Start it:

```bash
alphagsm myvanilla start
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

## Useful Commands

```bash
alphagsm myvanilla update
alphagsm myvanilla backup
```

## Notes

- Module name: `arma3.vanilla`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-vanilla/](../server-templates/arma3-vanilla/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
