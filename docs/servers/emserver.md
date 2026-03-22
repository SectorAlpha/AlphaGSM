# Empires Mod

This guide covers the `emserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myemserver create emserver
```

Run setup:

```bash
alphagsm myemserver setup
```

Start it:

```bash
alphagsm myemserver start
```

Check it:

```bash
alphagsm myemserver status
```

Stop it:

```bash
alphagsm myemserver stop
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
alphagsm myemserver update
alphagsm myemserver backup
```

## Notes

- Module name: `emserver`
- Default port: 27015
