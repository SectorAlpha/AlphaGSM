# Nightingale

This guide covers the `nightingale` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynighting create nightingale
```

Run setup:

```bash
alphagsm mynighting setup
```

Start it:

```bash
alphagsm mynighting start
```

Check it:

```bash
alphagsm mynighting status
```

Stop it:

```bash
alphagsm mynighting stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynighting update
alphagsm mynighting backup
```

## Notes

- Module name: `nightingale`
- Default port: 7777
