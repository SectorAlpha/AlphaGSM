# Core Keeper

This guide covers the `ckserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myckserver create ckserver
```

Run setup:

```bash
alphagsm myckserver setup
```

Start it:

```bash
alphagsm myckserver start
```

Check it:

```bash
alphagsm myckserver status
```

Stop it:

```bash
alphagsm myckserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myckserver update
alphagsm myckserver backup
```

## Notes

- Module name: `ckserver`
- Default port: 27015
