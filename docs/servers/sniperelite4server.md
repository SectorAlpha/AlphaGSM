# Sniper Elite 4

This guide covers the `sniperelite4server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysniperel create sniperelite4server
```

Run setup:

```bash
alphagsm mysniperel setup
```

Start it:

```bash
alphagsm mysniperel start
```

Check it:

```bash
alphagsm mysniperel status
```

Stop it:

```bash
alphagsm mysniperel stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysniperel update
alphagsm mysniperel backup
```

## Notes

- Module name: `sniperelite4server`
- Default port: 27015
