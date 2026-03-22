# Call of Duty

This guide covers the `codserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycodserve create codserver
```

Run setup:

```bash
alphagsm mycodserve setup
```

Start it:

```bash
alphagsm mycodserve start
```

Check it:

```bash
alphagsm mycodserve status
```

Stop it:

```bash
alphagsm mycodserve stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycodserve update
alphagsm mycodserve backup
```

## Notes

- Module name: `codserver`
- Default port: 28960
