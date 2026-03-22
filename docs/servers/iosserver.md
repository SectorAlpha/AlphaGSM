# IOSoccer

This guide covers the `iosserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myiosserve create iosserver
```

Run setup:

```bash
alphagsm myiosserve setup
```

Start it:

```bash
alphagsm myiosserve start
```

Check it:

```bash
alphagsm myiosserve status
```

Stop it:

```bash
alphagsm myiosserve stop
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
alphagsm myiosserve update
alphagsm myiosserve backup
```

## Notes

- Module name: `iosserver`
- Default port: 27015
