# Half-Life 2: Deathmatch

This guide covers the `hl2dmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhl2dmser create hl2dmserver
```

Run setup:

```bash
alphagsm myhl2dmser setup
```

Start it:

```bash
alphagsm myhl2dmser start
```

Check it:

```bash
alphagsm myhl2dmser status
```

Stop it:

```bash
alphagsm myhl2dmser stop
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
alphagsm myhl2dmser update
alphagsm myhl2dmser backup
```

## Notes

- Module name: `hl2dmserver`
- Default port: 27015
