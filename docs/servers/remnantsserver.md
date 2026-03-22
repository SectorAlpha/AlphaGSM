# Remnants

This guide covers the `remnantsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myremnants create remnantsserver
```

Run setup:

```bash
alphagsm myremnants setup
```

Start it:

```bash
alphagsm myremnants start
```

Check it:

```bash
alphagsm myremnants status
```

Stop it:

```bash
alphagsm myremnants stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myremnants update
alphagsm myremnants backup
```

## Notes

- Module name: `remnantsserver`
- Default port: 27015
