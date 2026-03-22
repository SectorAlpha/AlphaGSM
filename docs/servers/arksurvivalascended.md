# ARK: Survival Ascended

This guide covers the `arksurvivalascended` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarksurvi create arksurvivalascended
```

Run setup:

```bash
alphagsm myarksurvi setup
```

Start it:

```bash
alphagsm myarksurvi start
```

Check it:

```bash
alphagsm myarksurvi status
```

Stop it:

```bash
alphagsm myarksurvi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarksurvi update
alphagsm myarksurvi backup
```

## Notes

- Module name: `arksurvivalascended`
- Default port: 27015
