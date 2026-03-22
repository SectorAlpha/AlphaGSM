# BrainBread 2

This guide covers the `bb2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybb2serve create bb2server
```

Run setup:

```bash
alphagsm mybb2serve setup
```

Start it:

```bash
alphagsm mybb2serve start
```

Check it:

```bash
alphagsm mybb2serve status
```

Stop it:

```bash
alphagsm mybb2serve stop
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
alphagsm mybb2serve update
alphagsm mybb2serve backup
```

## Notes

- Module name: `bb2server`
- Default port: 27015
