# Sven Co-op

This guide covers the `svenserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysvenserv create svenserver
```

Run setup:

```bash
alphagsm mysvenserv setup
```

Start it:

```bash
alphagsm mysvenserv start
```

Check it:

```bash
alphagsm mysvenserv status
```

Stop it:

```bash
alphagsm mysvenserv stop
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
alphagsm mysvenserv update
alphagsm mysvenserv backup
```

## Notes

- Module name: `svenserver`
- Default port: 27015
