# BROKE PROTOCOL

This guide covers the `brokeprotocolserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybrokepro create brokeprotocolserver
```

Run setup:

```bash
alphagsm mybrokepro setup
```

Start it:

```bash
alphagsm mybrokepro start
```

Check it:

```bash
alphagsm mybrokepro status
```

Stop it:

```bash
alphagsm mybrokepro stop
```

## Setup Details

Setup configures:

- the game port (default 27777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybrokepro update
alphagsm mybrokepro backup
```

## Notes

- Module name: `brokeprotocolserver`
- Default port: 27777
