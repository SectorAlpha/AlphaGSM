# Wurm Unlimited

This guide covers the `wurmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywurmserv create wurmserver
```

Run setup:

```bash
alphagsm mywurmserv setup
```

Start it:

```bash
alphagsm mywurmserv start
```

Check it:

```bash
alphagsm mywurmserv status
```

Stop it:

```bash
alphagsm mywurmserv stop
```

## Setup Details

Setup configures:

- the game port (default 3724)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywurmserv update
alphagsm mywurmserv backup
```

## Notes

- Module name: `wurmserver`
- Default port: 3724
