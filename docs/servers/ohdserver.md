# Operation: Harsh Doorstop

This guide covers the `ohdserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myohdserve create ohdserver
```

Run setup:

```bash
alphagsm myohdserve setup
```

Start it:

```bash
alphagsm myohdserve start
```

Check it:

```bash
alphagsm myohdserve status
```

Stop it:

```bash
alphagsm myohdserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myohdserve update
alphagsm myohdserve backup
```

## Notes

- Module name: `ohdserver`
- Default port: 27015
