# StarRupture

This guide covers the `starruptureserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarrupt create starruptureserver
```

Run setup:

```bash
alphagsm mystarrupt setup
```

Start it:

```bash
alphagsm mystarrupt start
```

Check it:

```bash
alphagsm mystarrupt status
```

Stop it:

```bash
alphagsm mystarrupt stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystarrupt update
alphagsm mystarrupt backup
```

## Notes

- Module name: `starruptureserver`
- Default port: 7777
