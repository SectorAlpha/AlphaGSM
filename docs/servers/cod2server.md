# Call of Duty 2

This guide covers the `cod2server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycod2serv create cod2server
```

Run setup:

```bash
alphagsm mycod2serv setup
```

Start it:

```bash
alphagsm mycod2serv start
```

Check it:

```bash
alphagsm mycod2serv status
```

Stop it:

```bash
alphagsm mycod2serv stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycod2serv update
alphagsm mycod2serv backup
```

## Notes

- Module name: `cod2server`
- Default port: 28960
