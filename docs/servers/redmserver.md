# RedM

This guide covers the `redmserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myredmserv create redmserver
```

Run setup:

```bash
alphagsm myredmserv setup
```

Start it:

```bash
alphagsm myredmserv start
```

Check it:

```bash
alphagsm myredmserv status
```

Stop it:

```bash
alphagsm myredmserv stop
```

## Setup Details

Setup configures:

- the game port (default 30120)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myredmserv update
alphagsm myredmserv backup
```

## Notes

- Module name: `redmserver`
- Default port: 30120
