# 7 Days to Die

This guide covers the `sevendaystodie` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysevenday create sevendaystodie
```

Run setup:

```bash
alphagsm mysevenday setup
```

Start it:

```bash
alphagsm mysevenday start
```

Check it:

```bash
alphagsm mysevenday status
```

Stop it:

```bash
alphagsm mysevenday stop
```

## Setup Details

Setup configures:

- the game port (default 26900)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysevenday update
alphagsm mysevenday backup
```

## Notes

- Module name: `sevendaystodie`
- Default port: 26900
