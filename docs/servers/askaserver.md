# ASKA

This guide covers the `askaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaskaserv create askaserver
```

Run setup:

```bash
alphagsm myaskaserv setup
```

Start it:

```bash
alphagsm myaskaserv start
```

Check it:

```bash
alphagsm myaskaserv status
```

Stop it:

```bash
alphagsm myaskaserv stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myaskaserv update
alphagsm myaskaserv backup
```

## Notes

- Module name: `askaserver`
- Default port: 27016
