# Don't Starve Together

This guide covers the `dstserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydstserve create dstserver
```

Run setup:

```bash
alphagsm mydstserve setup
```

Start it:

```bash
alphagsm mydstserve start
```

Check it:

```bash
alphagsm mydstserve status
```

Stop it:

```bash
alphagsm mydstserve stop
```

## Setup Details

Setup configures:

- the game port (default 10999)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydstserve update
alphagsm mydstserve backup
```

## Notes

- Module name: `dstserver`
- Default port: 10999
