# PixARK

This guide covers the `pixarkserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypixarkse create pixarkserver
```

Run setup:

```bash
alphagsm mypixarkse setup
```

Start it:

```bash
alphagsm mypixarkse start
```

Check it:

```bash
alphagsm mypixarkse status
```

Stop it:

```bash
alphagsm mypixarkse stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypixarkse update
alphagsm mypixarkse backup
```

## Notes

- Module name: `pixarkserver`
- Default port: 27015
