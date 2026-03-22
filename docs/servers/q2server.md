# Quake 2

This guide covers the `q2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq2server create q2server
```

Run setup:

```bash
alphagsm myq2server setup
```

Start it:

```bash
alphagsm myq2server start
```

Check it:

```bash
alphagsm myq2server status
```

Stop it:

```bash
alphagsm myq2server stop
```

## Setup Details

Setup configures:

- the game port (default 27910)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq2server update
alphagsm myq2server backup
```

## Notes

- Module name: `q2server`
- Default port: 27910
