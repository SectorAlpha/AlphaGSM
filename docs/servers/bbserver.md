# BrainBread

This guide covers the `bbserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybbserver create bbserver
```

Run setup:

```bash
alphagsm mybbserver setup
```

Start it:

```bash
alphagsm mybbserver start
```

Check it:

```bash
alphagsm mybbserver status
```

Stop it:

```bash
alphagsm mybbserver stop
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
alphagsm mybbserver update
alphagsm mybbserver backup
```

## Notes

- Module name: `bbserver`
- Default port: 27015
