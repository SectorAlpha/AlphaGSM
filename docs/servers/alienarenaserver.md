# Alien Arena

This guide covers the `alienarenaserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myalienare create alienarenaserver
```

Run setup:

```bash
alphagsm myalienare setup
```

Start it:

```bash
alphagsm myalienare start
```

Check it:

```bash
alphagsm myalienare status
```

Stop it:

```bash
alphagsm myalienare stop
```

## Setup Details

Setup configures:

- the game port (default 27910)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myalienare update
alphagsm myalienare backup
```

## Notes

- Module name: `alienarenaserver`
- Default port: 27910
