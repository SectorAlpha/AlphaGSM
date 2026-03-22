# Battlefield Vietnam

This guide covers the `bfvserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybfvserve create bfvserver
```

Run setup:

```bash
alphagsm mybfvserve setup
```

Start it:

```bash
alphagsm mybfvserve start
```

Check it:

```bash
alphagsm mybfvserve status
```

Stop it:

```bash
alphagsm mybfvserve stop
```

## Setup Details

Setup configures:

- the game port (default 15567)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mybfvserve update
alphagsm mybfvserve backup
```

## Notes

- Module name: `bfvserver`
- Default port: 15567
