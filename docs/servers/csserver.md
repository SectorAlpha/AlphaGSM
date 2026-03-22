# Counter-Strike

This guide covers the `csserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycsserver create csserver
```

Run setup:

```bash
alphagsm mycsserver setup
```

Start it:

```bash
alphagsm mycsserver start
```

Check it:

```bash
alphagsm mycsserver status
```

Stop it:

```bash
alphagsm mycsserver stop
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
alphagsm mycsserver update
alphagsm mycsserver backup
```

## Notes

- Module name: `csserver`
- Default port: 27015
