# Day of Defeat

This guide covers the `dodserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydodserve create dodserver
```

Run setup:

```bash
alphagsm mydodserve setup
```

Start it:

```bash
alphagsm mydodserve start
```

Check it:

```bash
alphagsm mydodserve status
```

Stop it:

```bash
alphagsm mydodserve stop
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
alphagsm mydodserve update
alphagsm mydodserve backup
```

## Notes

- Module name: `dodserver`
- Default port: 27015
