# Motor Town: Behind The Wheel

This guide covers the `motortownserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymotortow create motortownserver
```

Run setup:

```bash
alphagsm mymotortow setup
```

Start it:

```bash
alphagsm mymotortow start
```

Check it:

```bash
alphagsm mymotortow status
```

Stop it:

```bash
alphagsm mymotortow stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymotortow update
alphagsm mymotortow backup
```

## Notes

- Module name: `motortownserver`
- Default port: 27015
