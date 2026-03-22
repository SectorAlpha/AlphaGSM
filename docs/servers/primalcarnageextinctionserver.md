# Primal Carnage: Extinction

This guide covers the `primalcarnageextinctionserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprimalca create primalcarnageextinctionserver
```

Run setup:

```bash
alphagsm myprimalca setup
```

Start it:

```bash
alphagsm myprimalca start
```

Check it:

```bash
alphagsm myprimalca status
```

Stop it:

```bash
alphagsm myprimalca stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myprimalca update
alphagsm myprimalca backup
```

## Notes

- Module name: `primalcarnageextinctionserver`
- Default port: 27015
