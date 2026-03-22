# The Specialists

This guide covers the `tsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytsserver create tsserver
```

Run setup:

```bash
alphagsm mytsserver setup
```

Start it:

```bash
alphagsm mytsserver start
```

Check it:

```bash
alphagsm mytsserver status
```

Stop it:

```bash
alphagsm mytsserver stop
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
alphagsm mytsserver update
alphagsm mytsserver backup
```

## Notes

- Module name: `tsserver`
- Default port: 27015
