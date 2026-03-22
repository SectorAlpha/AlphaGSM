# ASTRONEER

This guide covers the `astroneerserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myastronee create astroneerserver
```

Run setup:

```bash
alphagsm myastronee setup
```

Start it:

```bash
alphagsm myastronee start
```

Check it:

```bash
alphagsm myastronee status
```

Stop it:

```bash
alphagsm myastronee stop
```

## Setup Details

Setup configures:

- the game port (default 8777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myastronee update
alphagsm myastronee backup
```

## Notes

- Module name: `astroneerserver`
- Default port: 8777
