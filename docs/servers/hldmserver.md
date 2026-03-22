# Half-Life: Deathmatch

This guide covers the `hldmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhldmserv create hldmserver
```

Run setup:

```bash
alphagsm myhldmserv setup
```

Start it:

```bash
alphagsm myhldmserv start
```

Check it:

```bash
alphagsm myhldmserv status
```

Stop it:

```bash
alphagsm myhldmserv stop
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
alphagsm myhldmserv update
alphagsm myhldmserv backup
```

## Notes

- Module name: `hldmserver`
- Default port: 27015
