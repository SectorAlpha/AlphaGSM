# Dead Matter

This guide covers the `deadmatterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydeadmatt create deadmatterserver
```

Run setup:

```bash
alphagsm mydeadmatt setup
```

Start it:

```bash
alphagsm mydeadmatt start
```

Check it:

```bash
alphagsm mydeadmatt status
```

Stop it:

```bash
alphagsm mydeadmatt stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydeadmatt update
alphagsm mydeadmatt backup
```

## Notes

- Module name: `deadmatterserver`
- Default port: 27016
