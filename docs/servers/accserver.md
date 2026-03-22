# Assetto Corsa Competizione

This guide covers the `accserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaccserve create accserver
```

Run setup:

```bash
alphagsm myaccserve setup
```

Start it:

```bash
alphagsm myaccserve start
```

Check it:

```bash
alphagsm myaccserve status
```

Stop it:

```bash
alphagsm myaccserve stop
```

## Setup Details

Setup configures:

- the game port (default 9231)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myaccserve update
alphagsm myaccserve backup
```

## Notes

- Module name: `accserver`
- Default port: 9231
