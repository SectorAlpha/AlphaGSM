# No More Room in Hell

This guide covers the `nmrihserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynmrihser create nmrihserver
```

Run setup:

```bash
alphagsm mynmrihser setup
```

Start it:

```bash
alphagsm mynmrihser start
```

Check it:

```bash
alphagsm mynmrihser status
```

Stop it:

```bash
alphagsm mynmrihser stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm mynmrihser update
alphagsm mynmrihser backup
```

## Notes

- Module name: `nmrihserver`
- Default port: 27015
