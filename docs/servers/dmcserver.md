# Deathmatch Classic

This guide covers the `dmcserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydmcserve create dmcserver
```

Run setup:

```bash
alphagsm mydmcserve setup
```

Start it:

```bash
alphagsm mydmcserve start
```

Check it:

```bash
alphagsm mydmcserve status
```

Stop it:

```bash
alphagsm mydmcserve stop
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
alphagsm mydmcserve update
alphagsm mydmcserve backup
```

## Notes

- Module name: `dmcserver`
- Default port: 27015
