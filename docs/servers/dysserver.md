# Dystopia

This guide covers the `dysserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydysserve create dysserver
```

Run setup:

```bash
alphagsm mydysserve setup
```

Start it:

```bash
alphagsm mydysserve start
```

Check it:

```bash
alphagsm mydysserve status
```

Stop it:

```bash
alphagsm mydysserve stop
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
alphagsm mydysserve update
alphagsm mydysserve backup
```

## Notes

- Module name: `dysserver`
- Default port: 27015
