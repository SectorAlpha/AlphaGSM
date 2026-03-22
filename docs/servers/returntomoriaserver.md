# Return to Moria

This guide covers the `returntomoriaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreturnto create returntomoriaserver
```

Run setup:

```bash
alphagsm myreturnto setup
```

Start it:

```bash
alphagsm myreturnto start
```

Check it:

```bash
alphagsm myreturnto status
```

Stop it:

```bash
alphagsm myreturnto stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreturnto update
alphagsm myreturnto backup
```

## Notes

- Module name: `returntomoriaserver`
- Default port: 7777
