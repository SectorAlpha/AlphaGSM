# TerraTech Worlds

This guide covers the `terratechworldsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myterratec create terratechworldsserver
```

Run setup:

```bash
alphagsm myterratec setup
```

Start it:

```bash
alphagsm myterratec start
```

Check it:

```bash
alphagsm myterratec status
```

Stop it:

```bash
alphagsm myterratec stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myterratec update
alphagsm myterratec backup
```

## Notes

- Module name: `terratechworldsserver`
- Default port: 7777
