# Vampire Slayer

This guide covers the `vsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvsserver create vsserver
```

Run setup:

```bash
alphagsm myvsserver setup
```

Start it:

```bash
alphagsm myvsserver start
```

Check it:

```bash
alphagsm myvsserver status
```

Stop it:

```bash
alphagsm myvsserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myvsserver update
alphagsm myvsserver backup
```

## Notes

- Module name: `vsserver`
- Default port: 27015
