# Night of the Dead

This guide covers the `notdserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynotdserv create notdserver
```

Run setup:

```bash
alphagsm mynotdserv setup
```

Start it:

```bash
alphagsm mynotdserv start
```

Check it:

```bash
alphagsm mynotdserv status
```

Stop it:

```bash
alphagsm mynotdserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynotdserv update
alphagsm mynotdserv backup
```

## Notes

- Module name: `notdserver`
- Default port: 27015
