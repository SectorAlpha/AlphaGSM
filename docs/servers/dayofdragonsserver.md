# Day of Dragons

This guide covers the `dayofdragonsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayofdra create dayofdragonsserver
```

Run setup:

```bash
alphagsm mydayofdra setup
```

Start it:

```bash
alphagsm mydayofdra start
```

Check it:

```bash
alphagsm mydayofdra status
```

Stop it:

```bash
alphagsm mydayofdra stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayofdra update
alphagsm mydayofdra backup
```

## Notes

- Module name: `dayofdragonsserver`
- Default port: 27016
