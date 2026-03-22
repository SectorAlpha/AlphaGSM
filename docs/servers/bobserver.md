# Beasts of Bermuda

This guide covers the `bobserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybobserve create bobserver
```

Run setup:

```bash
alphagsm mybobserve setup
```

Start it:

```bash
alphagsm mybobserve start
```

Check it:

```bash
alphagsm mybobserve status
```

Stop it:

```bash
alphagsm mybobserve stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybobserve update
alphagsm mybobserve backup
```

## Notes

- Module name: `bobserver`
- Default port: 7778
