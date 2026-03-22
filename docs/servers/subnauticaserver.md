# Subnautica community

This guide covers the `subnauticaserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysubnauti create subnauticaserver
```

Run setup:

```bash
alphagsm mysubnauti setup
```

Start it:

```bash
alphagsm mysubnauti start
```

Check it:

```bash
alphagsm mysubnauti status
```

Stop it:

```bash
alphagsm mysubnauti stop
```

## Setup Details

Setup configures:

- the game port (default 11000)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mysubnauti update
alphagsm mysubnauti backup
```

## Notes

- Module name: `subnauticaserver`
- Default port: 11000
