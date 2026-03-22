# Ricochet

This guide covers the `ricochetserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myricochet create ricochetserver
```

Run setup:

```bash
alphagsm myricochet setup
```

Start it:

```bash
alphagsm myricochet start
```

Check it:

```bash
alphagsm myricochet status
```

Stop it:

```bash
alphagsm myricochet stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myricochet update
alphagsm myricochet backup
```

## Notes

- Module name: `ricochetserver`
- Default port: 27015
