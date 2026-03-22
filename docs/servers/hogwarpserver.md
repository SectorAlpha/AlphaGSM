# HogWarp

This guide covers the `hogwarpserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhogwarps create hogwarpserver
```

Run setup:

```bash
alphagsm myhogwarps setup
```

Start it:

```bash
alphagsm myhogwarps start
```

Check it:

```bash
alphagsm myhogwarps status
```

Stop it:

```bash
alphagsm myhogwarps stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myhogwarps update
alphagsm myhogwarps backup
```

## Notes

- Module name: `hogwarpserver`
- Default port: 7777
