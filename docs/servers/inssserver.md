# Insurgency: Sandstorm

This guide covers the `inssserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinssserv create inssserver
```

Run setup:

```bash
alphagsm myinssserv setup
```

Start it:

```bash
alphagsm myinssserv start
```

Check it:

```bash
alphagsm myinssserv status
```

Stop it:

```bash
alphagsm myinssserv stop
```

## Setup Details

Setup configures:

- the game port (default 27131)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myinssserv update
alphagsm myinssserv backup
```

## Notes

- Module name: `inssserver`
- Default port: 27131
