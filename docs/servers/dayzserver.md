# DayZ

This guide covers the `dayzserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayzserv create dayzserver
```

Run setup:

```bash
alphagsm mydayzserv setup
```

Start it:

```bash
alphagsm mydayzserv start
```

Check it:

```bash
alphagsm mydayzserv status
```

Stop it:

```bash
alphagsm mydayzserv stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayzserv update
alphagsm mydayzserv backup
```

## Notes

- Module name: `dayzserver`
- Default port: 2302
