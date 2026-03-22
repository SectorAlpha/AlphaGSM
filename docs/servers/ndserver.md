# Nuclear Dawn

This guide covers the `ndserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myndserver create ndserver
```

Run setup:

```bash
alphagsm myndserver setup
```

Start it:

```bash
alphagsm myndserver start
```

Check it:

```bash
alphagsm myndserver status
```

Stop it:

```bash
alphagsm myndserver stop
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
alphagsm myndserver update
alphagsm myndserver backup
```

## Notes

- Module name: `ndserver`
- Default port: 27015
