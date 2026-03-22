# Action: Source

This guide covers the `ahl2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myahl2serv create ahl2server
```

Run setup:

```bash
alphagsm myahl2serv setup
```

Start it:

```bash
alphagsm myahl2serv start
```

Check it:

```bash
alphagsm myahl2serv status
```

Stop it:

```bash
alphagsm myahl2serv stop
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
alphagsm myahl2serv update
alphagsm myahl2serv backup
```

## Notes

- Module name: `ahl2server`
- Default port: 27015
