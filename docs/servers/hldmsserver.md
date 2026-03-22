# Half-Life Deathmatch: Source

This guide covers the `hldmsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhldmsser create hldmsserver
```

Run setup:

```bash
alphagsm myhldmsser setup
```

Start it:

```bash
alphagsm myhldmsser start
```

Check it:

```bash
alphagsm myhldmsser status
```

Stop it:

```bash
alphagsm myhldmsser stop
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
alphagsm myhldmsser update
alphagsm myhldmsser backup
```

## Notes

- Module name: `hldmsserver`
- Default port: 27015
