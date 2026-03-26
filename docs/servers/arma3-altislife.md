# Namespaced Arma 3 Altis Life

This guide covers the `arma3.altislife` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaltislif create arma3.altislife
```

Run setup:

```bash
alphagsm myaltislif setup
```

Start it:

```bash
alphagsm myaltislif start
```

Check it:

```bash
alphagsm myaltislif status
```

Stop it:

```bash
alphagsm myaltislif stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm myaltislif update
alphagsm myaltislif backup
```

## Notes

- Module name: `arma3.altislife`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-altislife/](../server-templates/arma3-altislife/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
