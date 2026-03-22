# Double Action: Boogaloo

This guide covers the `dabserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydabserve create dabserver
```

Run setup:

```bash
alphagsm mydabserve setup
```

Start it:

```bash
alphagsm mydabserve start
```

Check it:

```bash
alphagsm mydabserve status
```

Stop it:

```bash
alphagsm mydabserve stop
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
alphagsm mydabserve update
alphagsm mydabserve backup
```

## Notes

- Module name: `dabserver`
- Default port: 27015
