# Arma 3 Altis Life

This guide covers the `arma3altislifeserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3alt create arma3altislifeserver
```

Run setup:

```bash
alphagsm myarma3alt setup
```

Start it:

```bash
alphagsm myarma3alt start
```

Check it:

```bash
alphagsm myarma3alt status
```

Stop it:

```bash
alphagsm myarma3alt stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3alt update
alphagsm myarma3alt backup
```

## Notes

- Module name: `arma3altislifeserver`
- Default port: 2302
