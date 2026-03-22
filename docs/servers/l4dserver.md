# Left 4 Dead

This guide covers the `l4dserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myl4dserve create l4dserver
```

Run setup:

```bash
alphagsm myl4dserve setup
```

Start it:

```bash
alphagsm myl4dserve start
```

Check it:

```bash
alphagsm myl4dserve status
```

Stop it:

```bash
alphagsm myl4dserve stop
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
alphagsm myl4dserve update
alphagsm myl4dserve backup
```

## Notes

- Module name: `l4dserver`
- Default port: 27015
