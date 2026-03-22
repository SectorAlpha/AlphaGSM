# Miscreated

This guide covers the `miscreatedserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymiscreat create miscreatedserver
```

Run setup:

```bash
alphagsm mymiscreat setup
```

Start it:

```bash
alphagsm mymiscreat start
```

Check it:

```bash
alphagsm mymiscreat status
```

Stop it:

```bash
alphagsm mymiscreat stop
```

## Setup Details

Setup configures:

- the game port (default 64090)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymiscreat update
alphagsm mymiscreat backup
```

## Notes

- Module name: `miscreatedserver`
- Default port: 64090
