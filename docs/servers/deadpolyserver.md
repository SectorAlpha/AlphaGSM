# DeadPoly

This guide covers the `deadpolyserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydeadpoly create deadpolyserver
```

Run setup:

```bash
alphagsm mydeadpoly setup
```

Start it:

```bash
alphagsm mydeadpoly start
```

Check it:

```bash
alphagsm mydeadpoly status
```

Stop it:

```bash
alphagsm mydeadpoly stop
```

## Setup Details

Setup configures:

- the game port (default 7779)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydeadpoly update
alphagsm mydeadpoly backup
```

## Notes

- Module name: `deadpolyserver`
- Default port: 7779
