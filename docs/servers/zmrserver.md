# Zombie Master: Reborn

This guide covers the `zmrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myzmrserve create zmrserver
```

Run setup:

```bash
alphagsm myzmrserve setup
```

Start it:

```bash
alphagsm myzmrserve start
```

Check it:

```bash
alphagsm myzmrserve status
```

Stop it:

```bash
alphagsm myzmrserve stop
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
alphagsm myzmrserve update
alphagsm myzmrserve backup
```

## Notes

- Module name: `zmrserver`
- Default port: 27015
