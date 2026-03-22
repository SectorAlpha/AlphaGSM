# Craftopia

This guide covers the `craftopiaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycraftopi create craftopiaserver
```

Run setup:

```bash
alphagsm mycraftopi setup
```

Start it:

```bash
alphagsm mycraftopi start
```

Check it:

```bash
alphagsm mycraftopi status
```

Stop it:

```bash
alphagsm mycraftopi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycraftopi update
alphagsm mycraftopi backup
```

## Notes

- Module name: `craftopiaserver`
- Default port: 27015
