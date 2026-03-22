# Abiotic Factor

This guide covers the `abfserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myabfserve create abfserver
```

Run setup:

```bash
alphagsm myabfserve setup
```

Start it:

```bash
alphagsm myabfserve start
```

Check it:

```bash
alphagsm myabfserve status
```

Stop it:

```bash
alphagsm myabfserve stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myabfserve update
alphagsm myabfserve backup
```

## Notes

- Module name: `abfserver`
- Default port: 27016
