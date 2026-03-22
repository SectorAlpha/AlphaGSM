# Natural Selection

This guide covers the `nsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynsserver create nsserver
```

Run setup:

```bash
alphagsm mynsserver setup
```

Start it:

```bash
alphagsm mynsserver start
```

Check it:

```bash
alphagsm mynsserver status
```

Stop it:

```bash
alphagsm mynsserver stop
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
alphagsm mynsserver update
alphagsm mynsserver backup
```

## Notes

- Module name: `nsserver`
- Default port: 27015
