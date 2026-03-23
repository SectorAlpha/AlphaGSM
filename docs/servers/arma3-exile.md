# Namespaced Arma 3 Exile

This guide covers the `arma3.exile` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myexile create arma3.exile
```

Run setup:

```bash
alphagsm myexile setup
```

Start it:

```bash
alphagsm myexile start
```

Check it:

```bash
alphagsm myexile status
```

Stop it:

```bash
alphagsm myexile stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm myexile update
alphagsm myexile backup
```

## Notes

- Module name: `arma3.exile`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-exile/](../server-templates/arma3-exile/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
