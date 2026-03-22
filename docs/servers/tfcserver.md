# Team Fortress Classic

This guide covers the `tfcserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytfcserve create tfcserver
```

Run setup:

```bash
alphagsm mytfcserve setup
```

Start it:

```bash
alphagsm mytfcserve start
```

Check it:

```bash
alphagsm mytfcserve status
```

Stop it:

```bash
alphagsm mytfcserve stop
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
alphagsm mytfcserve update
alphagsm mytfcserve backup
```

## Notes

- Module name: `tfcserver`
- Default port: 27015
