# Last Oasis

This guide covers the `lastoasisserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylastoasi create lastoasisserver
```

Run setup:

```bash
alphagsm mylastoasi setup
```

Start it:

```bash
alphagsm mylastoasi start
```

Check it:

```bash
alphagsm mylastoasi status
```

Stop it:

```bash
alphagsm mylastoasi stop
```

## Setup Details

Setup configures:

- the game port (default 15001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylastoasi update
alphagsm mylastoasi backup
```

## Notes

- Module name: `lastoasisserver`
- Default port: 15001
