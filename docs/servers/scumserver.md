# SCUM

This guide covers the `scumserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myscumserv create scumserver
```

Run setup:

```bash
alphagsm myscumserv setup
```

Start it:

```bash
alphagsm myscumserv start
```

Check it:

```bash
alphagsm myscumserv status
```

Stop it:

```bash
alphagsm myscumserv stop
```

## Setup Details

Setup configures:

- the game port (default 7779)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myscumserv update
alphagsm myscumserv backup
```

## Notes

- Module name: `scumserver`
- Default port: 7779
