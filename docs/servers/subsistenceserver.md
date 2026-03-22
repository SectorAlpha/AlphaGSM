# Subsistence

This guide covers the `subsistenceserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysubsiste create subsistenceserver
```

Run setup:

```bash
alphagsm mysubsiste setup
```

Start it:

```bash
alphagsm mysubsiste start
```

Check it:

```bash
alphagsm mysubsiste status
```

Stop it:

```bash
alphagsm mysubsiste stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysubsiste update
alphagsm mysubsiste backup
```

## Notes

- Module name: `subsistenceserver`
- Default port: 27016
