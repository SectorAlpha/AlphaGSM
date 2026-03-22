# Action Half-Life

This guide covers the `ahlserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myahlserve create ahlserver
```

Run setup:

```bash
alphagsm myahlserve setup
```

Start it:

```bash
alphagsm myahlserve start
```

Check it:

```bash
alphagsm myahlserve status
```

Stop it:

```bash
alphagsm myahlserve stop
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
alphagsm myahlserve update
alphagsm myahlserve backup
```

## Notes

- Module name: `ahlserver`
- Default port: 27015
