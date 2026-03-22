# Argo

This guide covers the `argoserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myargoserv create argoserver
```

Run setup:

```bash
alphagsm myargoserv setup
```

Start it:

```bash
alphagsm myargoserv start
```

Check it:

```bash
alphagsm myargoserv status
```

Stop it:

```bash
alphagsm myargoserv stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myargoserv update
alphagsm myargoserv backup
```

## Notes

- Module name: `argoserver`
- Default port: 2302
