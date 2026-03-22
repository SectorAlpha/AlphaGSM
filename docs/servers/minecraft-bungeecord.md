# Collect and store configuration values for a Bungeecord

This guide covers the `minecraft.bungeecord` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybungeeco create minecraft.bungeecord
```

Run setup:

```bash
alphagsm mybungeeco setup
```

Start it:

```bash
alphagsm mybungeeco start
```

Check it:

```bash
alphagsm mybungeeco status
```

Stop it:

```bash
alphagsm mybungeeco stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mybungeeco update
alphagsm mybungeeco backup
```

## Notes

- Module name: `minecraft.bungeecord`
- Default port: 27015
