# Namespaced Arma 3 Desolation Redux

This guide covers the `arma3.desolationredux` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydesolati create arma3.desolationredux
```

Run setup:

```bash
alphagsm mydesolati setup
```

Start it:

```bash
alphagsm mydesolati start
```

Check it:

```bash
alphagsm mydesolati status
```

Stop it:

```bash
alphagsm mydesolati stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mydesolati update
alphagsm mydesolati backup
```

## Notes

- Module name: `arma3.desolationredux`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: See game module source
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/arma3-desolationredux/](../server-templates/arma3-desolationredux/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
