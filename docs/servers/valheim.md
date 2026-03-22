# Valheim

This guide covers the `valheim` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvalheim create valheim
```

Run setup:

```bash
alphagsm myvalheim setup
```

Start it:

```bash
alphagsm myvalheim start
```

Check it:

```bash
alphagsm myvalheim status
```

Stop it:

```bash
alphagsm myvalheim stop
```

## Setup Details

Setup configures:

- the game port (default 2456)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myvalheim update
alphagsm myvalheim backup
```

## Notes

- Module name: `valheim`
- Default port: 2456
