# Myth of Empires

This guide covers the `mythofempiresserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymythofem create mythofempiresserver
```

Run setup:

```bash
alphagsm mymythofem setup
```

Start it:

```bash
alphagsm mymythofem start
```

Check it:

```bash
alphagsm mymythofem status
```

Stop it:

```bash
alphagsm mymythofem stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymythofem update
alphagsm mymythofem backup
```

## Notes

- Module name: `mythofempiresserver`
- Default port: 27015
