# Quake 4

This guide covers the `q4server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq4server create q4server
```

Run setup:

```bash
alphagsm myq4server setup
```

Start it:

```bash
alphagsm myq4server start
```

Check it:

```bash
alphagsm myq4server status
```

Stop it:

```bash
alphagsm myq4server stop
```

## Setup Details

Setup configures:

- the game port (default 28004)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq4server update
alphagsm myq4server backup
```

## Notes

- Module name: `q4server`
- Default port: 28004
