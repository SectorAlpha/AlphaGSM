# Space Engineers

This guide covers the `seserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myseserver create seserver
```

Run setup:

```bash
alphagsm myseserver setup
```

Start it:

```bash
alphagsm myseserver start
```

Check it:

```bash
alphagsm myseserver status
```

Stop it:

```bash
alphagsm myseserver stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myseserver update
alphagsm myseserver backup
```

## Notes

- Module name: `seserver`
- Default port: 27016
