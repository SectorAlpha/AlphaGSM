# Police 1013

This guide covers the `police1013server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypolice10 create police1013server
```

Run setup:

```bash
alphagsm mypolice10 setup
```

Start it:

```bash
alphagsm mypolice10 start
```

Check it:

```bash
alphagsm mypolice10 status
```

Stop it:

```bash
alphagsm mypolice10 stop
```

## Setup Details

Setup configures:

- the game port (default 1013)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypolice10 update
alphagsm mypolice10 backup
```

## Notes

- Module name: `police1013server`
- Default port: 1013
