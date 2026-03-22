# Squad

This guide covers the `squadserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquadser create squadserver
```

Run setup:

```bash
alphagsm mysquadser setup
```

Start it:

```bash
alphagsm mysquadser start
```

Check it:

```bash
alphagsm mysquadser status
```

Stop it:

```bash
alphagsm mysquadser stop
```

## Setup Details

Setup configures:

- the game port (default 27165)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquadser update
alphagsm mysquadser backup
```

## Notes

- Module name: `squadserver`
- Default port: 27165
