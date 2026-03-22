# Smalland

This guide covers the `smallandserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysmalland create smallandserver
```

Run setup:

```bash
alphagsm mysmalland setup
```

Start it:

```bash
alphagsm mysmalland start
```

Check it:

```bash
alphagsm mysmalland status
```

Stop it:

```bash
alphagsm mysmalland stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysmalland update
alphagsm mysmalland backup
```

## Notes

- Module name: `smallandserver`
- Default port: 7778
