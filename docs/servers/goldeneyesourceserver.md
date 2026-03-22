# GoldenEye: Source

This guide covers the `goldeneyesourceserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygoldeney create goldeneyesourceserver
```

Run setup:

```bash
alphagsm mygoldeney setup
```

Start it:

```bash
alphagsm mygoldeney start
```

Check it:

```bash
alphagsm mygoldeney status
```

Stop it:

```bash
alphagsm mygoldeney stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mygoldeney update
alphagsm mygoldeney backup
```

## Notes

- Module name: `goldeneyesourceserver`
- Default port: 27015
