# American Truck Simulator

This guide covers the `atsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myatsserve create atsserver
```

Run setup:

```bash
alphagsm myatsserve setup
```

Start it:

```bash
alphagsm myatsserve start
```

Check it:

```bash
alphagsm myatsserve status
```

Stop it:

```bash
alphagsm myatsserve stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myatsserve update
alphagsm myatsserve backup
```

## Notes

- Module name: `atsserver`
- Default port: 27016
