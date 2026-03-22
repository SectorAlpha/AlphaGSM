# San Andreas Multiplayer

This guide covers the `sampserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysampserv create sampserver
```

Run setup:

```bash
alphagsm mysampserv setup
```

Start it:

```bash
alphagsm mysampserv start
```

Check it:

```bash
alphagsm mysampserv status
```

Stop it:

```bash
alphagsm mysampserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mysampserv update
alphagsm mysampserv backup
```

## Notes

- Module name: `sampserver`
- Default port: 7777
