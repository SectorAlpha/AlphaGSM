# Counter-Strike: Source

This guide covers the `cssserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycssserve create cssserver
```

Run setup:

```bash
alphagsm mycssserve setup
```

Start it:

```bash
alphagsm mycssserve start
```

Check it:

```bash
alphagsm mycssserve status
```

Stop it:

```bash
alphagsm mycssserve stop
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
alphagsm mycssserve update
alphagsm mycssserve backup
```

## Notes

- Module name: `cssserver`
- Default port: 27015
