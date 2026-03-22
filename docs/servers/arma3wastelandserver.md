# Arma 3 Wasteland

This guide covers the `arma3wastelandserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3was create arma3wastelandserver
```

Run setup:

```bash
alphagsm myarma3was setup
```

Start it:

```bash
alphagsm myarma3was start
```

Check it:

```bash
alphagsm myarma3was status
```

Stop it:

```bash
alphagsm myarma3was stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3was update
alphagsm myarma3was backup
```

## Notes

- Module name: `arma3wastelandserver`
- Default port: 2302
