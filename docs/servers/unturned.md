# Unturned

This guide covers the `unturned` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myunturned create unturned
```

Run setup:

```bash
alphagsm myunturned setup
```

Start it:

```bash
alphagsm myunturned start
```

Check it:

```bash
alphagsm myunturned status
```

Stop it:

```bash
alphagsm myunturned stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myunturned update
alphagsm myunturned backup
```

## Notes

- Module name: `unturned`
- Default port: 27015
