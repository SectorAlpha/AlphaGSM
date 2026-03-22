# Arma 3

This guide covers the `arma3server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3ser create arma3server
```

Run setup:

```bash
alphagsm myarma3ser setup
```

Start it:

```bash
alphagsm myarma3ser start
```

Check it:

```bash
alphagsm myarma3ser status
```

Stop it:

```bash
alphagsm myarma3ser stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3ser update
alphagsm myarma3ser backup
```

## Notes

- Module name: `arma3server`
- Default port: 2302
