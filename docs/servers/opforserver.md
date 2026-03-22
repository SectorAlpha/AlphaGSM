# Opposing Force

This guide covers the `opforserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myopforser create opforserver
```

Run setup:

```bash
alphagsm myopforser setup
```

Start it:

```bash
alphagsm myopforser start
```

Check it:

```bash
alphagsm myopforser status
```

Stop it:

```bash
alphagsm myopforser stop
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
alphagsm myopforser update
alphagsm myopforser backup
```

## Notes

- Module name: `opforserver`
- Default port: 27015
