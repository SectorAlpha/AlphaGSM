# Soldat

This guide covers the `solserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysolserve create solserver
```

Run setup:

```bash
alphagsm mysolserve setup
```

Start it:

```bash
alphagsm mysolserve start
```

Check it:

```bash
alphagsm mysolserve status
```

Stop it:

```bash
alphagsm mysolserve stop
```

## Setup Details

Setup configures:

- the game port (default 23073)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysolserve update
alphagsm mysolserve backup
```

## Notes

- Module name: `solserver`
- Default port: 23073
