# Blade Symphony

This guide covers the `bsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybsserver create bsserver
```

Run setup:

```bash
alphagsm mybsserver setup
```

Start it:

```bash
alphagsm mybsserver start
```

Check it:

```bash
alphagsm mybsserver status
```

Stop it:

```bash
alphagsm mybsserver stop
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
alphagsm mybsserver update
alphagsm mybsserver backup
```

## Notes

- Module name: `bsserver`
- Default port: 27015
