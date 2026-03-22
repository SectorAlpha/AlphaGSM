# Trackmania

This guide covers the `trackmaniaserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytrackman create trackmaniaserver
```

Run setup:

```bash
alphagsm mytrackman setup
```

Start it:

```bash
alphagsm mytrackman start
```

Check it:

```bash
alphagsm mytrackman status
```

Stop it:

```bash
alphagsm mytrackman stop
```

## Setup Details

Setup configures:

- the game port (default 5000)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mytrackman update
alphagsm mytrackman backup
```

## Notes

- Module name: `trackmaniaserver`
- Default port: 5000
