# Brickadia

This guide covers the `brickadiaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybrickadi create brickadiaserver
```

Run setup:

```bash
alphagsm mybrickadi setup
```

Start it:

```bash
alphagsm mybrickadi start
```

Check it:

```bash
alphagsm mybrickadi status
```

Stop it:

```bash
alphagsm mybrickadi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybrickadi update
alphagsm mybrickadi backup
```

## Notes

- Module name: `brickadiaserver`
- Default port: 27015
