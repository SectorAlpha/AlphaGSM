# Ready or Not

This guide covers the `readyornotserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreadyorn create readyornotserver
```

Run setup:

```bash
alphagsm myreadyorn setup
```

Start it:

```bash
alphagsm myreadyorn start
```

Check it:

```bash
alphagsm myreadyorn status
```

Stop it:

```bash
alphagsm myreadyorn stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreadyorn update
alphagsm myreadyorn backup
```

## Notes

- Module name: `readyornotserver`
- Default port: 27015
