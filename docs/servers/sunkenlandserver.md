# Sunkenland

This guide covers the `sunkenlandserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysunkenla create sunkenlandserver
```

Run setup:

```bash
alphagsm mysunkenla setup
```

Start it:

```bash
alphagsm mysunkenla start
```

Check it:

```bash
alphagsm mysunkenla status
```

Stop it:

```bash
alphagsm mysunkenla stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysunkenla update
alphagsm mysunkenla backup
```

## Notes

- Module name: `sunkenlandserver`
- Default port: 27015
