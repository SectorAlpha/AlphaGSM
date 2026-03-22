# Mount & Blade II: Bannerlord

This guide covers the `bannerlordserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybannerlo create bannerlordserver
```

Run setup:

```bash
alphagsm mybannerlo setup
```

Start it:

```bash
alphagsm mybannerlo start
```

Check it:

```bash
alphagsm mybannerlo status
```

Stop it:

```bash
alphagsm mybannerlo stop
```

## Setup Details

Setup configures:

- the game port (default 7210)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybannerlo update
alphagsm mybannerlo backup
```

## Notes

- Module name: `bannerlordserver`
- Default port: 7210
