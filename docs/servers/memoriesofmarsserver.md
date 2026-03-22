# Memories of Mars

This guide covers the `memoriesofmarsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymemories create memoriesofmarsserver
```

Run setup:

```bash
alphagsm mymemories setup
```

Start it:

```bash
alphagsm mymemories start
```

Check it:

```bash
alphagsm mymemories status
```

Stop it:

```bash
alphagsm mymemories stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymemories update
alphagsm mymemories backup
```

## Notes

- Module name: `memoriesofmarsserver`
- Default port: 27015
