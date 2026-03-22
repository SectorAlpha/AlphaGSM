# Mordhau

This guide covers the `mordserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymordserv create mordserver
```

Run setup:

```bash
alphagsm mymordserv setup
```

Start it:

```bash
alphagsm mymordserv start
```

Check it:

```bash
alphagsm mymordserv status
```

Stop it:

```bash
alphagsm mymordserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymordserv update
alphagsm mymordserv backup
```

## Notes

- Module name: `mordserver`
- Default port: 27015
