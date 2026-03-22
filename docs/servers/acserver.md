# Assetto Corsa

This guide covers the `acserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myacserver create acserver
```

Run setup:

```bash
alphagsm myacserver setup
```

Start it:

```bash
alphagsm myacserver start
```

Check it:

```bash
alphagsm myacserver status
```

Stop it:

```bash
alphagsm myacserver stop
```

## Setup Details

Setup configures:

- the game port (default 8081)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myacserver update
alphagsm myacserver backup
```

## Notes

- Module name: `acserver`
- Default port: 8081
