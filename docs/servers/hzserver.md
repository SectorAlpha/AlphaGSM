# Humanitz

This guide covers the `hzserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhzserver create hzserver
```

Run setup:

```bash
alphagsm myhzserver setup
```

Start it:

```bash
alphagsm myhzserver start
```

Check it:

```bash
alphagsm myhzserver status
```

Stop it:

```bash
alphagsm myhzserver stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myhzserver update
alphagsm myhzserver backup
```

## Notes

- Module name: `hzserver`
- Default port: 27016
