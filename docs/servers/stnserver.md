# Survive the Nights

This guide covers the `stnserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystnserve create stnserver
```

Run setup:

```bash
alphagsm mystnserve setup
```

Start it:

```bash
alphagsm mystnserve start
```

Check it:

```bash
alphagsm mystnserve status
```

Stop it:

```bash
alphagsm mystnserve stop
```

## Setup Details

Setup configures:

- the game port (default 8888)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystnserve update
alphagsm mystnserve backup
```

## Notes

- Module name: `stnserver`
- Default port: 8888
