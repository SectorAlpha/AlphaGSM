# Citadel: Forged With Fire

This guide covers the `citadelserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycitadels create citadelserver
```

Run setup:

```bash
alphagsm mycitadels setup
```

Start it:

```bash
alphagsm mycitadels start
```

Check it:

```bash
alphagsm mycitadels status
```

Stop it:

```bash
alphagsm mycitadels stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycitadels update
alphagsm mycitadels backup
```

## Notes

- Module name: `citadelserver`
- Default port: 27015
