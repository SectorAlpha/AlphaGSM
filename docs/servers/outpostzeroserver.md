# Outpost Zero

This guide covers the `outpostzeroserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myoutpostz create outpostzeroserver
```

Run setup:

```bash
alphagsm myoutpostz setup
```

Start it:

```bash
alphagsm myoutpostz start
```

Check it:

```bash
alphagsm myoutpostz status
```

Stop it:

```bash
alphagsm myoutpostz stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myoutpostz update
alphagsm myoutpostz backup
```

## Notes

- Module name: `outpostzeroserver`
- Default port: 27015
