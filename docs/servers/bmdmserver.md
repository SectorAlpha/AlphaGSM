# Black Mesa: Deathmatch

This guide covers the `bmdmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybmdmserv create bmdmserver
```

Run setup:

```bash
alphagsm mybmdmserv setup
```

Start it:

```bash
alphagsm mybmdmserv start
```

Check it:

```bash
alphagsm mybmdmserv status
```

Stop it:

```bash
alphagsm mybmdmserv stop
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
alphagsm mybmdmserv update
alphagsm mybmdmserv backup
```

## Notes

- Module name: `bmdmserver`
- Default port: 27015
