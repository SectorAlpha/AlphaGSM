# Base Defense

This guide covers the `bdserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybdserver create bdserver
```

Run setup:

```bash
alphagsm mybdserver setup
```

Start it:

```bash
alphagsm mybdserver start
```

Check it:

```bash
alphagsm mybdserver status
```

Stop it:

```bash
alphagsm mybdserver stop
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
alphagsm mybdserver update
alphagsm mybdserver backup
```

## Notes

- Module name: `bdserver`
- Default port: 27015
