# V Rising

This guide covers the `vrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvrserver create vrserver
```

Run setup:

```bash
alphagsm myvrserver setup
```

Start it:

```bash
alphagsm myvrserver start
```

Check it:

```bash
alphagsm myvrserver status
```

Stop it:

```bash
alphagsm myvrserver stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myvrserver update
alphagsm myvrserver backup
```

## Notes

- Module name: `vrserver`
- Default port: 27016
