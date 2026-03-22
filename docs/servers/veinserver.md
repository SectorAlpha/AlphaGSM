# VEIN

This guide covers the `veinserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myveinserv create veinserver
```

Run setup:

```bash
alphagsm myveinserv setup
```

Start it:

```bash
alphagsm myveinserv start
```

Check it:

```bash
alphagsm myveinserv status
```

Stop it:

```bash
alphagsm myveinserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myveinserv update
alphagsm myveinserv backup
```

## Notes

- Module name: `veinserver`
- Default port: 27015
