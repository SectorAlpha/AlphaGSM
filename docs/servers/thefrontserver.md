# The Front

This guide covers the `thefrontserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mythefront create thefrontserver
```

Run setup:

```bash
alphagsm mythefront setup
```

Start it:

```bash
alphagsm mythefront start
```

Check it:

```bash
alphagsm mythefront status
```

Stop it:

```bash
alphagsm mythefront stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mythefront update
alphagsm mythefront backup
```

## Notes

- Module name: `thefrontserver`
- Default port: 27015
