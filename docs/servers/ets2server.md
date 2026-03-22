# Euro Truck Simulator 2

This guide covers the `ets2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myets2serv create ets2server
```

Run setup:

```bash
alphagsm myets2serv setup
```

Start it:

```bash
alphagsm myets2serv start
```

Check it:

```bash
alphagsm myets2serv status
```

Stop it:

```bash
alphagsm myets2serv stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myets2serv update
alphagsm myets2serv backup
```

## Notes

- Module name: `ets2server`
- Default port: 27016
