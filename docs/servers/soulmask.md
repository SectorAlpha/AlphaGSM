# Soulmask

This guide covers the `soulmask` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysoulmask create soulmask
```

Run setup:

```bash
alphagsm mysoulmask setup
```

Start it:

```bash
alphagsm mysoulmask start
```

Check it:

```bash
alphagsm mysoulmask status
```

Stop it:

```bash
alphagsm mysoulmask stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysoulmask update
alphagsm mysoulmask backup
```

## Notes

- Module name: `soulmask`
- Default port: 27015
