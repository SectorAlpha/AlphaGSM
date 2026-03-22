# Chivalry: Medieval Warfare

This guide covers the `chivalryserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mychivalry create chivalryserver
```

Run setup:

```bash
alphagsm mychivalry setup
```

Start it:

```bash
alphagsm mychivalry start
```

Check it:

```bash
alphagsm mychivalry status
```

Stop it:

```bash
alphagsm mychivalry stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mychivalry update
alphagsm mychivalry backup
```

## Notes

- Module name: `chivalryserver`
- Default port: 7777
