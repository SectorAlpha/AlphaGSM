# Reign Of Dwarf

This guide covers the `reignofdwarfserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreignofd create reignofdwarfserver
```

Run setup:

```bash
alphagsm myreignofd setup
```

Start it:

```bash
alphagsm myreignofd start
```

Check it:

```bash
alphagsm myreignofd status
```

Stop it:

```bash
alphagsm myreignofd stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreignofd update
alphagsm myreignofd backup
```

## Notes

- Module name: `reignofdwarfserver`
- Default port: 27015
