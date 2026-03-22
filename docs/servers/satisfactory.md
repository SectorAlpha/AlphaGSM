# Satisfactory

This guide covers the `satisfactory` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysatisfac create satisfactory
```

Run setup:

```bash
alphagsm mysatisfac setup
```

Start it:

```bash
alphagsm mysatisfac start
```

Check it:

```bash
alphagsm mysatisfac status
```

Stop it:

```bash
alphagsm mysatisfac stop
```

## Setup Details

Setup configures:

- the game port (default 15777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysatisfac update
alphagsm mysatisfac backup
```

## Notes

- Module name: `satisfactory`
- Default port: 15777
