# Pirates Vikings & Knights II

This guide covers the `pvkiiserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypvkiiser create pvkiiserver
```

Run setup:

```bash
alphagsm mypvkiiser setup
```

Start it:

```bash
alphagsm mypvkiiser start
```

Check it:

```bash
alphagsm mypvkiiser status
```

Stop it:

```bash
alphagsm mypvkiiser stop
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
alphagsm mypvkiiser update
alphagsm mypvkiiser backup
```

## Notes

- Module name: `pvkiiserver`
- Default port: 27015
