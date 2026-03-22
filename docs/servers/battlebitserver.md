# BattleBit Remastered

This guide covers the `battlebitserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybattlebi create battlebitserver
```

Run setup:

```bash
alphagsm mybattlebi setup
```

Start it:

```bash
alphagsm mybattlebi start
```

Check it:

```bash
alphagsm mybattlebi status
```

Stop it:

```bash
alphagsm mybattlebi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybattlebi update
alphagsm mybattlebi backup
```

## Notes

- Module name: `battlebitserver`
- Default port: 27015
