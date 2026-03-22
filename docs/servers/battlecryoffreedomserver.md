# Battle Cry of Freedom

This guide covers the `battlecryoffreedomserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybattlecr create battlecryoffreedomserver
```

Run setup:

```bash
alphagsm mybattlecr setup
```

Start it:

```bash
alphagsm mybattlecr start
```

Check it:

```bash
alphagsm mybattlecr status
```

Stop it:

```bash
alphagsm mybattlecr stop
```

## Setup Details

Setup configures:

- the game port (default 8263)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybattlecr update
alphagsm mybattlecr backup
```

## Notes

- Module name: `battlecryoffreedomserver`
- Default port: 8263
