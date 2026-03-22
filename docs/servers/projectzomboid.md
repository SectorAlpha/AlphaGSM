# Project Zomboid

This guide covers the `projectzomboid` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprojectz create projectzomboid
```

Run setup:

```bash
alphagsm myprojectz setup
```

Start it:

```bash
alphagsm myprojectz start
```

Check it:

```bash
alphagsm myprojectz status
```

Stop it:

```bash
alphagsm myprojectz stop
```

## Setup Details

Setup configures:

- the game port (default 16261)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myprojectz update
alphagsm myprojectz backup
```

## Notes

- Module name: `projectzomboid`
- Default port: 16261
