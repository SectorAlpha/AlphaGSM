# Longvinter

This guide covers the `longvinterserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylongvint create longvinterserver
```

Run setup:

```bash
alphagsm mylongvint setup
```

Start it:

```bash
alphagsm mylongvint start
```

Check it:

```bash
alphagsm mylongvint status
```

Stop it:

```bash
alphagsm mylongvint stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylongvint update
alphagsm mylongvint backup
```

## Notes

- Module name: `longvinterserver`
- Default port: 7777
