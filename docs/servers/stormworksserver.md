# Stormworks

This guide covers the `stormworksserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystormwor create stormworksserver
```

Run setup:

```bash
alphagsm mystormwor setup
```

Start it:

```bash
alphagsm mystormwor start
```

Check it:

```bash
alphagsm mystormwor status
```

Stop it:

```bash
alphagsm mystormwor stop
```

## Setup Details

Setup configures:

- the game port (default 25566)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystormwor update
alphagsm mystormwor backup
```

## Notes

- Module name: `stormworksserver`
- Default port: 25566
