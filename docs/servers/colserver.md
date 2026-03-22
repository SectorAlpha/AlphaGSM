# Colony Survival

This guide covers the `colserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycolserve create colserver
```

Run setup:

```bash
alphagsm mycolserve setup
```

Start it:

```bash
alphagsm mycolserve start
```

Check it:

```bash
alphagsm mycolserve status
```

Stop it:

```bash
alphagsm mycolserve stop
```

## Setup Details

Setup configures:

- the game port (default 27004)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycolserve update
alphagsm mycolserve backup
```

## Notes

- Module name: `colserver`
- Default port: 27004
