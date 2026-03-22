# Day of Defeat: Source

This guide covers the `dodsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydodsserv create dodsserver
```

Run setup:

```bash
alphagsm mydodsserv setup
```

Start it:

```bash
alphagsm mydodsserv start
```

Check it:

```bash
alphagsm mydodsserv status
```

Stop it:

```bash
alphagsm mydodsserv stop
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
alphagsm mydodsserv update
alphagsm mydodsserv backup
```

## Notes

- Module name: `dodsserver`
- Default port: 27015
