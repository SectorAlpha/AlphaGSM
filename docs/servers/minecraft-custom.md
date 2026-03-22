# Common Minecraft

This guide covers the `minecraft.custom` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycustom create minecraft.custom
```

Run setup:

```bash
alphagsm mycustom setup
```

Start it:

```bash
alphagsm mycustom start
```

Check it:

```bash
alphagsm mycustom status
```

Stop it:

```bash
alphagsm mycustom stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mycustom update
alphagsm mycustom backup
```

## Notes

- Module name: `minecraft.custom`
- Default port: 27015
