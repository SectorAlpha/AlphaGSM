# Project CARS

This guide covers the `pcarserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypcarserv create pcarserver
```

Run setup:

```bash
alphagsm mypcarserv setup
```

Start it:

```bash
alphagsm mypcarserv start
```

Check it:

```bash
alphagsm mypcarserv status
```

Stop it:

```bash
alphagsm mypcarserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypcarserv update
alphagsm mypcarserv backup
```

## Notes

- Module name: `pcarserver`
- Default port: 27015
