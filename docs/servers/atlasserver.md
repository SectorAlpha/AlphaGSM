# ATLAS

This guide covers the `atlasserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myatlasser create atlasserver
```

Run setup:

```bash
alphagsm myatlasser setup
```

Start it:

```bash
alphagsm myatlasser start
```

Check it:

```bash
alphagsm myatlasser status
```

Stop it:

```bash
alphagsm myatlasser stop
```

## Setup Details

Setup configures:

- the game port (default 57561)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myatlasser update
alphagsm myatlasser backup
```

## Notes

- Module name: `atlasserver`
- Default port: 57561
