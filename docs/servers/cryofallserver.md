# CryoFall

This guide covers the `cryofallserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycryofall create cryofallserver
```

Run setup:

```bash
alphagsm mycryofall setup
```

Start it:

```bash
alphagsm mycryofall start
```

Check it:

```bash
alphagsm mycryofall status
```

Stop it:

```bash
alphagsm mycryofall stop
```

## Setup Details

Setup configures:

- the game port (default 49001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycryofall update
alphagsm mycryofall backup
```

## Notes

- Module name: `cryofallserver`
- Default port: 49001
