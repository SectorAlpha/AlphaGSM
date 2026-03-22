# Stationeers

This guide covers the `stationeersserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystatione create stationeersserver
```

Run setup:

```bash
alphagsm mystatione setup
```

Start it:

```bash
alphagsm mystatione start
```

Check it:

```bash
alphagsm mystatione status
```

Stop it:

```bash
alphagsm mystatione stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystatione update
alphagsm mystatione backup
```

## Notes

- Module name: `stationeersserver`
- Default port: 27015
