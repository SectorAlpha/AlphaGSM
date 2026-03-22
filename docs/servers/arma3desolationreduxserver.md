# Arma 3 Desolation Redux

This guide covers the `arma3desolationreduxserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarma3des create arma3desolationreduxserver
```

Run setup:

```bash
alphagsm myarma3des setup
```

Start it:

```bash
alphagsm myarma3des start
```

Check it:

```bash
alphagsm myarma3des status
```

Stop it:

```bash
alphagsm myarma3des stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarma3des update
alphagsm myarma3des backup
```

## Notes

- Module name: `arma3desolationreduxserver`
- Default port: 2302
