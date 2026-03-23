# Namespaced Arma 3 Wasteland

This guide covers the `arma3.wasteland` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywastelan create arma3.wasteland
```

Run setup:

```bash
alphagsm mywastelan setup
```

Start it:

```bash
alphagsm mywastelan start
```

Check it:

```bash
alphagsm mywastelan status
```

Stop it:

```bash
alphagsm mywastelan stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mywastelan update
alphagsm mywastelan backup
```

## Notes

- Module name: `arma3.wasteland`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-wasteland/](../server-templates/arma3-wasteland/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
