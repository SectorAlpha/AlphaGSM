# Rising World

This guide covers the `rwserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrwserver create rwserver
```

Run setup:

```bash
alphagsm myrwserver setup
```

Start it:

```bash
alphagsm myrwserver start
```

Check it:

```bash
alphagsm myrwserver status
```

Stop it:

```bash
alphagsm myrwserver stop
```

## Setup Details

Setup configures:

- the game port (default 4254)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myrwserver update
alphagsm myrwserver backup
```

## Notes

- Module name: `rwserver`
- Default port: 4254
