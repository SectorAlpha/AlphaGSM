# Codename CURE

This guide covers the `ccserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myccserver create ccserver
```

Run setup:

```bash
alphagsm myccserver setup
```

Start it:

```bash
alphagsm myccserver start
```

Check it:

```bash
alphagsm myccserver status
```

Stop it:

```bash
alphagsm myccserver stop
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
alphagsm myccserver update
alphagsm myccserver backup
```

## Notes

- Module name: `ccserver`
- Default port: 27015
