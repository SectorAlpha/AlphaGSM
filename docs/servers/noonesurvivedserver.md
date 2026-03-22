# No One Survived

This guide covers the `noonesurvivedserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynoonesur create noonesurvivedserver
```

Run setup:

```bash
alphagsm mynoonesur setup
```

Start it:

```bash
alphagsm mynoonesur start
```

Check it:

```bash
alphagsm mynoonesur status
```

Stop it:

```bash
alphagsm mynoonesur stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynoonesur update
alphagsm mynoonesur backup
```

## Notes

- Module name: `noonesurvivedserver`
- Default port: 27015
