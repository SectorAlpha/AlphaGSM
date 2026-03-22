# Zombie Panic! Source

This guide covers the `zpsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myzpsserve create zpsserver
```

Run setup:

```bash
alphagsm myzpsserve setup
```

Start it:

```bash
alphagsm myzpsserve start
```

Check it:

```bash
alphagsm myzpsserve status
```

Stop it:

```bash
alphagsm myzpsserve stop
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
alphagsm myzpsserve update
alphagsm myzpsserve backup
```

## Notes

- Module name: `zpsserver`
- Default port: 27015
