# Arma Reforger

This guide covers the `armarserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarmarser create armarserver
```

Run setup:

```bash
alphagsm myarmarser setup
```

Start it:

```bash
alphagsm myarmarser start
```

Check it:

```bash
alphagsm myarmarser status
```

Stop it:

```bash
alphagsm myarmarser stop
```

## Setup Details

Setup configures:

- the game port (default 2001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarmarser update
alphagsm myarmarser backup
```

## Notes

- Module name: `armarserver`
- Default port: 2001
