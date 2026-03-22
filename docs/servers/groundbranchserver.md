# GROUND BRANCH

This guide covers the `groundbranchserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygroundbr create groundbranchserver
```

Run setup:

```bash
alphagsm mygroundbr setup
```

Start it:

```bash
alphagsm mygroundbr start
```

Check it:

```bash
alphagsm mygroundbr status
```

Stop it:

```bash
alphagsm mygroundbr stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mygroundbr update
alphagsm mygroundbr backup
```

## Notes

- Module name: `groundbranchserver`
- Default port: 27015
