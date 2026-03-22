# Frozen Flame

This guide covers the `frozenflameserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfrozenfl create frozenflameserver
```

Run setup:

```bash
alphagsm myfrozenfl setup
```

Start it:

```bash
alphagsm myfrozenfl start
```

Check it:

```bash
alphagsm myfrozenfl status
```

Stop it:

```bash
alphagsm myfrozenfl stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myfrozenfl update
alphagsm myfrozenfl backup
```

## Notes

- Module name: `frozenflameserver`
- Default port: 27015
