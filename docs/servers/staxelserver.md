# Staxel

This guide covers the `staxelserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystaxelse create staxelserver
```

Run setup:

```bash
alphagsm mystaxelse setup
```

Start it:

```bash
alphagsm mystaxelse start
```

Check it:

```bash
alphagsm mystaxelse status
```

Stop it:

```bash
alphagsm mystaxelse stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystaxelse update
alphagsm mystaxelse backup
```

## Notes

- Module name: `staxelserver`
- Default port: 25565
