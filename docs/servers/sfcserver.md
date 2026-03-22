# SourceForts Classic

This guide covers the `sfcserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysfcserve create sfcserver
```

Run setup:

```bash
alphagsm mysfcserve setup
```

Start it:

```bash
alphagsm mysfcserve start
```

Check it:

```bash
alphagsm mysfcserve status
```

Stop it:

```bash
alphagsm mysfcserve stop
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
alphagsm mysfcserve update
alphagsm mysfcserve backup
```

## Notes

- Module name: `sfcserver`
- Default port: 27015
