# Enshrouded

This guide covers the `enshrouded` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myenshroud create enshrouded
```

Run setup:

```bash
alphagsm myenshroud setup
```

Start it:

```bash
alphagsm myenshroud start
```

Check it:

```bash
alphagsm myenshroud status
```

Stop it:

```bash
alphagsm myenshroud stop
```

## Setup Details

Setup configures:

- the game port (default 15638)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myenshroud update
alphagsm myenshroud backup
```

## Notes

- Module name: `enshrouded`
- Default port: 15638
