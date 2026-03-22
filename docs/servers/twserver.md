# Teeworlds

This guide covers the `twserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytwserver create twserver
```

Run setup:

```bash
alphagsm mytwserver setup
```

Start it:

```bash
alphagsm mytwserver start
```

Check it:

```bash
alphagsm mytwserver status
```

Stop it:

```bash
alphagsm mytwserver stop
```

## Setup Details

Setup configures:

- the game port (default 8303)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mytwserver update
alphagsm mytwserver backup
```

## Notes

- Module name: `twserver`
- Default port: 8303
