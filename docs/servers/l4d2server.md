# Left 4 Dead 2

This guide covers the `l4d2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myl4d2serv create l4d2server
```

Run setup:

```bash
alphagsm myl4d2serv setup
```

Start it:

```bash
alphagsm myl4d2serv start
```

Check it:

```bash
alphagsm myl4d2serv status
```

Stop it:

```bash
alphagsm myl4d2serv stop
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
alphagsm myl4d2serv update
alphagsm myl4d2serv backup
```

## Notes

- Module name: `l4d2server`
- Default port: 27015
