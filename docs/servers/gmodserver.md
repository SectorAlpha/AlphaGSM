# Garrys Mod

This guide covers the `gmodserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygmodserv create gmodserver
```

Run setup:

```bash
alphagsm mygmodserv setup
```

Start it:

```bash
alphagsm mygmodserv start
```

Check it:

```bash
alphagsm mygmodserv status
```

Stop it:

```bash
alphagsm mygmodserv stop
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
alphagsm mygmodserv update
alphagsm mygmodserv backup
```

## Notes

- Module name: `gmodserver`
- Default port: 27015
