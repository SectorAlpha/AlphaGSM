# Quake 3 Arena

This guide covers the `q3server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myq3server create q3server
```

Run setup:

```bash
alphagsm myq3server setup
```

Start it:

```bash
alphagsm myq3server start
```

Check it:

```bash
alphagsm myq3server status
```

Stop it:

```bash
alphagsm myq3server stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myq3server update
alphagsm myq3server backup
```

## Notes

- Module name: `q3server`
- Default port: 27960
