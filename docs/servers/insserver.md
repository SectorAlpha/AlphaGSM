# Insurgency

This guide covers the `insserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinsserve create insserver
```

Run setup:

```bash
alphagsm myinsserve setup
```

Start it:

```bash
alphagsm myinsserve start
```

Check it:

```bash
alphagsm myinsserve status
```

Stop it:

```bash
alphagsm myinsserve stop
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
alphagsm myinsserve update
alphagsm myinsserve backup
```

## Notes

- Module name: `insserver`
- Default port: 27015
